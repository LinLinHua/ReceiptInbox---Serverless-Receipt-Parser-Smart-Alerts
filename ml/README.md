# ML Pipeline - Receipt Processing

Python-based ML pipeline for receipt OCR, categorization, and anomaly detection.

## Components

- `sqs_handler.py` - SQS message processor (entry point)
- `parse_rekognition.py` - AWS Rekognition OCR
- `categorize_bedrock.py` - AWS Bedrock AI categorization
- `anomalies.py` - Anomaly detection logic
- `schemas.py` - Pydantic data models
- `config.py` - Configuration and logging

## How It Works

1. **Trigger**: SQS message from API Lambda
2. **OCR**: Extract text from receipt image (Rekognition)
3. **Parse**: Extract merchant, amounts, date
4. **Categorize**: AI categorization (Bedrock Claude 3)
5. **Detect**: Check for anomalies
6. **Notify**: Send alerts via SNS if anomalies found
7. **Save**: Update DynamoDB with results

## Anomaly Detection

- **High Total**: Amount > $200
- **Math Error**: Subtotal + Tax != Total (>5% difference)
- **Duplicate**: Same merchant + date + amount

## Categories

Groceries, Restaurants, Entertainment, Travel, Transportation, Gas, Shopping, Health, Utilities, Subscriptions, Education, Home, Personal Care, Insurance, Other

## Dependencies

See `requirements.txt`:
- boto3 (AWS SDK)
- pydantic (Data validation)

## Configuration

Environment variables (set in SAM template):
- `S3_BUCKET_RECEIPTS` - Input bucket
- `S3_BUCKET_OUTPUT` - Output bucket
- `DYNAMODB_TABLE` - Metadata table
- `BEDROCK_MODEL_ID` - AI model
- `HIGH_TOTAL_THRESHOLD` - Anomaly threshold
- `ANOMALY_TOPIC_ARN` - SNS topic
- `BEDROCK_ACCESS_KEY` - Cross-account key (optional)
- `BEDROCK_SECRET_KEY` - Cross-account secret (optional)
