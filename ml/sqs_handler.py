import json
import os
import traceback
import boto3
from typing import Any, Dict
from datetime import datetime
from decimal import Decimal

# Import ML modules (absolute imports for Lambda)
import parse_rekognition
import ocr_rekognition
import categorize
import anomalies
import config

logger = config.get_logger(__name__)

# Helper function to convert floats to Decimal for DynamoDB
def convert_floats_to_decimal(obj):
    """Convert all float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    return obj

# AWS clients
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'ReceiptMetadata')
table = dynamodb.Table(DYNAMODB_TABLE)
ANOMALY_TOPIC_ARN = os.environ.get('ANOMALY_TOPIC_ARN', '')

S3_BUCKET_RECEIPTS = os.environ.get('S3_BUCKET_RECEIPTS')
S3_BUCKET_OUTPUT = os.environ.get('S3_BUCKET_OUTPUT', S3_BUCKET_RECEIPTS)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Received SQS event with {len(event.get('Records', []))} messages")
    
    # Process each SQS message
    for record in event.get('Records', []):
        try:
            # Parse SQS message body
            message_body = json.loads(record['body'])
            logger.info(f"Processing message: {message_body}")
            
            job_id = message_body['job_id']
            user_id = message_body['user_id']
            s3_key = message_body['s3_key']
            
            # Process the receipt
            result = process_receipt(job_id, user_id, s3_key)
            
            # Update DynamoDB with results
            update_dynamodb(user_id, job_id, result)
            
            logger.info(f"Successfully processed job {job_id}")
            
        except Exception as e:
            logger.error(f"Error processing SQS message: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try to update DynamoDB with error status
            try:
                if 'job_id' in locals() and 'user_id' in locals():
                    table.update_item(
                        Key={'user_id': user_id, 'receipt_id': job_id},
                        UpdateExpression='SET #status = :status, #error = :error',
                        ExpressionAttributeNames={
                            '#status': 'status',
                            '#error': 'error'
                        },
                        ExpressionAttributeValues={
                            ':status': 'FAILED',
                            ':error': str(e)
                        }
                    )
            except Exception as db_error:
                logger.error(f"Failed to update DynamoDB with error: {db_error}")
    
    return {"statusCode": 200, "body": "Processing complete"}


def process_receipt(job_id: str, user_id: str, s3_key: str) -> Dict[str, Any]:
    logger.info(f"Processing receipt: job_id={job_id}, s3_key={s3_key}")
    
    # Step 1: Run Rekognition OCR
    logger.info(f"Running Rekognition on s3://{S3_BUCKET_RECEIPTS}/{s3_key}")
    rekognition_response = ocr_rekognition.run_rekognition_on_s3_object(
        bucket=S3_BUCKET_RECEIPTS,
        key=s3_key
    )
    
    # Step 2: Save raw output (optional, for debugging)
    rekognition_output_key = f"rekognition-output/{job_id}.json"
    ocr_rekognition.save_rekognition_output_to_s3(
        rekognition_response=rekognition_response,
        output_bucket=S3_BUCKET_OUTPUT,
        output_key=rekognition_output_key
    )
    
    # Step 3: Parse Rekognition response
    logger.info("Parsing Rekognition response")
    parsed_receipt = parse_rekognition.parse_rekognition_response(
        job_id=job_id,
        user_id=user_id,
        rekognition_response=rekognition_response,
        rekognition_s3_key=rekognition_output_key
    )
    
    # Step 4: Categorize with Bedrock
    logger.info("Running categorization")
    parsed_receipt = categorize.categorize_parsed_receipt(parsed_receipt, use_ml=True)
    
    # Step 5: Detect anomalies
    logger.info("Running anomaly detection")
    alerts = anomalies.detect_anomalies(parsed_receipt)
    
    # Package results
    result = {
        "parsed_receipt": parsed_receipt.model_dump(),
        "alerts": [alert.model_dump() for alert in alerts]
    }
    
    logger.info(f"Processing complete: {len(parsed_receipt.items)} items, {len(alerts)} alerts")
    
    # Send SNS notification if anomalies detected
    if alerts and ANOMALY_TOPIC_ARN:
        send_anomaly_notification(job_id, parsed_receipt, alerts)
    
    return result


def update_dynamodb(user_id: str, job_id: str, result: Dict[str, Any]):
    parsed = result['parsed_receipt']
    alerts = result['alerts']
    
    # Prepare update expression
    update_expr = """
        SET #status = :status,
            merchant = :merchant,
            merchant_name = :merchant_name,
            purchase_date = :date,
            subtotal = :subtotal,
            tax = :tax,
            #total = :total,
            total_amount = :total_amount,
            amount = :amount,
            category = :category,
            category_confidence = :confidence,
            categorization_method = :method,
            alerts = :alerts,
            processed_at = :processed_at
    """
    
    # Get category info from first item (all items have same category)
    category = "Other"
    category_confidence = 0.0
    categorization_method = "Unknown"
    
    if parsed.get('items') and len(parsed['items']) > 0:
        first_item = parsed['items'][0]
        category = first_item.get('category', 'Other')
        category_confidence = first_item.get('category_confidence', 0.0)
    
    # Determine method from logs 
    categorization_method = "ML (Bedrock/Claude)" if category_confidence > 0.85 else "Rule-based"
    
    try:
        table.update_item(
            Key={
                'user_id': user_id,
                'receipt_id': job_id
            },
            UpdateExpression=update_expr,
            ExpressionAttributeNames={
                '#status': 'status',
                '#total': 'total'
            },
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':merchant': parsed.get('merchant') or 'Unknown',
                ':merchant_name': parsed.get('merchant') or 'Unknown',
                ':date': parsed.get('purchase_date'),
                ':subtotal': convert_floats_to_decimal(parsed.get('subtotal')),
                ':tax': convert_floats_to_decimal(parsed.get('tax')),
                ':total': convert_floats_to_decimal(parsed.get('total')),
                ':total_amount': str(parsed.get('total') or '0.00'),
                ':category': category,
                ':confidence': convert_floats_to_decimal(category_confidence),
                ':method': categorization_method,
                ':alerts': convert_floats_to_decimal(alerts),
                ':processed_at': datetime.utcnow().isoformat(),
                ':amount': str(parsed.get('total') or '0.00')
            }
        )
        logger.info(f"Updated DynamoDB for job {job_id}")
    except Exception as e:
        logger.error(f"Failed to update DynamoDB: {e}")
        raise


def send_anomaly_notification(job_id: str, parsed_receipt, alerts: list):
    """Send SNS notification for detected anomalies."""
    try:
        merchant = parsed_receipt.merchant or 'Unknown'
        total = parsed_receipt.total or 0.0
        alert_messages = []
        for alert in alerts:
            if isinstance(alert, dict):
                alert_messages.append(f"- {alert['type']}: {alert['message']}")
            else:
                alert_messages.append(f"- {alert.type}: {alert.message}")
        
        alert_text = "\n".join(alert_messages)
        
        message = f"""🚨 Anomaly Detected on Receipt

Receipt ID: {job_id}
Merchant: {merchant}
Amount: ${total:.2f}

Anomalies Detected:
{alert_text}

review this receipt in your dashboard.
"""
        
        sns_client.publish(
            TopicArn=ANOMALY_TOPIC_ARN,
            Subject=f"⚠️ Receipt Anomaly Alert - {merchant}",
            Message=message
        )
        logger.info(f"Anomaly notification sent for receipt {job_id}")
    except Exception as e:
        logger.error(f"Failed to send anomaly notification: {str(e)}")

