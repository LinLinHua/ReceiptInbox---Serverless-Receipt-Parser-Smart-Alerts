import os
import json
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum
from jose import jwt, JWTError

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
SECRET_KEY = "supersecretkey-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BUCKET_NAME = os.environ.get("RECEIPT_BUCKET_NAME", "receipt-inbox-uploads-ml-stack-v2")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "ReceiptMetadata-ML-v2")
ANOMALY_TOPIC_ARN = os.environ.get("ANOMALY_TOPIC_ARN", "")

# --- AWS Clients ---
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
receipts_table = dynamodb.Table(DYNAMODB_TABLE)
users_table = dynamodb.Table("Users-ML-v2")  # We'll create this

import hashlib

# --- Security Setup ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Pydantic Schemas ---
class UserSignup(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Helper Functions ---
def verify_password(plain_password, hashed_password):
    # Use SHA256 for password hashing
    password_hash = hashlib.sha256(plain_password.encode()).hexdigest()
    return password_hash == hashed_password

def get_password_hash(password):
    # Use SHA256 for password hashing
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    try:
        response = users_table.get_item(Key={'username': username})
        if 'Item' not in response:
            raise credentials_exception
        return response['Item']
    except:
        raise credentials_exception

# --- Authentication Endpoints ---
@app.post("/signup", response_model=Token)
def signup(user: UserSignup):
    """Create user in DynamoDB and return JWT"""
    try:
        # Check if user exists
        response = users_table.get_item(Key={'username': user.username})
        if 'Item' in response:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Create user
        hashed_password = get_password_hash(user.password)
        users_table.put_item(
            Item={
                'username': user.username,
                'password_hash': hashed_password,
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        # Return JWT
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signup error: {str(e)}")

@app.post("/login", response_model=Token)
def login(user: UserSignup):
    """Validate credentials and return JWT"""
    try:
        response = users_table.get_item(Key={'username': user.username})
        if 'Item' not in response:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        db_user = response['Item']
        if not verify_password(user.password, db_user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

# --- CORS Preflight Handler ---
@app.options("/")
@app.options("/{path:path}")
async def options_handler(path: str = ""):
    """Handle CORS preflight requests"""
    return {"status": "ok"}

# --- Receipt Upload Endpoint ---
@app.post("/")
async def upload_receipt(file: UploadFile = File(...)):
    """Upload receipt and trigger ML processing"""
    try:
        # Use a test user for now
        test_user = {'username': 'testuser'}
        # Generate unique IDs
        receipt_id = str(uuid.uuid4())
        s3_key = f"receipts/{test_user['username']}/{receipt_id}_{file.filename}"
        
        # Upload to S3
        file_content = await file.read()
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type
        )
        
        # Create initial DynamoDB entry
        receipts_table.put_item(
            Item={
                'user_id': test_user['username'],
                'receipt_id': receipt_id,
                's3_key': s3_key,
                'status': 'PROCESSING',
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        # Send SQS message to trigger ML processing
        if QUEUE_URL:
            message = {
                "job_id": receipt_id,
                "user_id": test_user['username'],
                "s3_key": s3_key
            }
            sqs_client.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message)
            )
        
        return {
            "receipt_id": receipt_id,
            "status": "PROCESSING",
            "message": "Receipt uploaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# --- Receipt Image Endpoint ---
@app.get("/receipts/{receipt_id}/image")
def get_receipt_image(receipt_id: str):
    """Generate presigned URL for receipt image"""
    try:
        # Scan for receipt (no GSI available)
        response = receipts_table.scan(
            FilterExpression='receipt_id = :rid',
            ExpressionAttributeValues={':rid': receipt_id}
        )
        
        if not response.get('Items'):
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        receipt = response['Items'][0]
        s3_key = receipt.get('s3_key')
        
        if not s3_key:
            raise HTTPException(status_code=404, detail="Receipt image not found")
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        return {"image_url": presigned_url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- Receipt Retrieval Endpoints ---
@app.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single processed receipt"""
    try:
        response = receipts_table.get_item(
            Key={
                'user_id': current_user['username'],
                'receipt_id': receipt_id
            }
        )
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        return response['Item']
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/receipts")
def list_receipts():
    """List all receipts for test user"""
    try:
        response = receipts_table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={
                ':uid': 'testuser'
            },
            ScanIndexForward=False
        )
        
        return {"receipts": response.get('Items', [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# --- Admin Endpoints for Testing ---
@app.post("/admin/complete-receipt/{receipt_id}")
def complete_receipt_manually(receipt_id: str):
    """Manually complete a receipt with sample data (for testing when ML fails)"""
    try:
        import random
        
        # Scan for the receipt
        response = receipts_table.scan(
            FilterExpression='receipt_id = :rid',
            ExpressionAttributeValues={':rid': receipt_id}
        )
        
        if not response.get('Items'):
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        receipt = response['Items'][0]
        
        # Varied sample data for better visualization
        merchants = ["Walmart", "Target", "Whole Foods", "Costco", "Amazon", "Starbucks", "McDonald's"]
        categories = ["Groceries", "Shopping", "Food & Dining", "Transportation", "Entertainment"]
        amounts = ["15.99", "25.50", "42.75", "67.20", "89.99", "12.45", "34.80", "56.30"]
        
        # Update with random sample data
        receipts_table.update_item(
            Key={
                'user_id': receipt['user_id'],
                'receipt_id': receipt_id
            },
            UpdateExpression='SET #status = :status, merchant_name = :merchant, total_amount = :amount, category = :category, purchase_date = :date',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':merchant': random.choice(merchants),
                ':amount': random.choice(amounts),
                ':category': random.choice(categories),
                ':date': datetime.utcnow().strftime('%Y-%m-%d')
            }
        )
        
        return {"message": "Receipt completed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/admin/clear-all-receipts")
def clear_all_receipts():
    """Delete all receipts for testuser (for testing)"""
    try:
        # Query all receipts for testuser
        response = receipts_table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': 'testuser'}
        )
        
        # Delete each receipt
        for item in response.get('Items', []):
            receipts_table.delete_item(
                Key={
                    'user_id': item['user_id'],
                    'receipt_id': item['receipt_id']
                }
            )
        
        return {"message": f"Deleted {len(response.get('Items', []))} receipts"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/admin/add-anomalies/{receipt_id}")
def add_anomalies_to_receipt(receipt_id: str):
    """Add sample anomalies to a receipt for testing"""
    try:
        # Scan for the receipt
        response = receipts_table.scan(
            FilterExpression='receipt_id = :rid',
            ExpressionAttributeValues={':rid': receipt_id}
        )
        
        if not response.get('Items'):
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        receipt = response['Items'][0]
        
        # Sample anomalies
        anomalies = [
            "Unusually high amount for this merchant",
            "Purchase made outside business hours"
        ]
        
        # Add anomalies and complete the receipt
        receipts_table.update_item(
            Key={
                'user_id': receipt['user_id'],
                'receipt_id': receipt_id
            },
            UpdateExpression='SET anomalies = :anomalies, #status = :status, merchant_name = :merchant, total_amount = :amount, category = :category',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':anomalies': anomalies,
                ':status': 'COMPLETED',
                ':merchant': 'Luxury Store',
                ':amount': '999.99',
                ':category': 'Shopping'
            }
        )
        
        # Send email notification
        send_anomaly_notification(receipt_id, 'Luxury Store', '999.99', anomalies)
        
        return {"message": "Anomalies added and notification sent successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/admin/subscribe-anomaly-alerts")
def subscribe_to_anomaly_alerts(email: str):
    """Subscribe an email to anomaly notifications"""
    try:
        if not ANOMALY_TOPIC_ARN:
            raise HTTPException(status_code=500, detail="SNS topic not configured")
        
        response = sns_client.subscribe(
            TopicArn=ANOMALY_TOPIC_ARN,
            Protocol='email',
            Endpoint=email
        )
        
        return {
            "message": f"Confirmation email sent to {email}. Please check your inbox and confirm the subscription.",
            "subscription_arn": response.get('SubscriptionArn', 'pending confirmation')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

def send_anomaly_notification(receipt_id: str, merchant: str, amount: str, anomalies: list):
    """Send SNS notification for detected anomalies"""
    try:
        if not ANOMALY_TOPIC_ARN:
            print("Warning: SNS topic not configured, skipping notification")
            return
        
        message = f
        
        sns_client.publish(
            TopicArn=ANOMALY_TOPIC_ARN,
            Subject=f"⚠️ Receipt Anomaly Alert - {merchant}",
            Message=message
        )
        print(f"Anomaly notification sent for receipt {receipt_id}")
    except Exception as e:
        print(f"Error sending notification: {str(e)}")

handler = Mangum(app)