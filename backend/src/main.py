import os
import json
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from mangum import Mangum
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError

# Import models from your local file
from models import SessionLocal, User

app = FastAPI()

# --- Configuration ---
# In production, fetch these from AWS Secrets Manager
SECRET_KEY = "supersecretkey" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BUCKET_NAME = os.environ.get("RECEIPT_BUCKET_NAME")
# We will add this env var to template.yaml in the next step
QUEUE_URL = os.environ.get("SQS_QUEUE_URL") 
DYNAMODB_TABLE = "ReceiptMetadata"

# --- AWS Clients ---
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)

# --- Security Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# This tells FastAPI that the token is found in the "Authorization: Bearer" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Pydantic Schemas ---
class UserSignup(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UploadRequest(BaseModel):
    file_name: str
    content_type: str

class TaskRequest(BaseModel):
    s3_key: str

# --- Helper Functions ---
def get_db():
    """Dependency to get DB session per request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    """Generates a JWT token [cite: 73]"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Decodes JWT to identify the user making the request"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- 1. Authentication Endpoints ---

@app.post("/auth/signup", response_model=Token)
def signup(user: UserSignup, db: Session = Depends(get_db)):
    """
    Create user in PostgreSQL and return JWT[cite: 73].
    """
    # Check if user already exists in PostgreSQL
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and save to PostgreSQL [cite: 83]
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, password_hash=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Return JWT
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
def login(user: UserSignup, db: Session = Depends(get_db)):
    """
    Validate credentials against PostgreSQL and return JWT[cite: 75, 84].
    """
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- 2. Receipt Upload Endpoints ---

@app.post("/receipts/upload-url")
def get_presigned_url(request: UploadRequest, current_user: User = Depends(get_current_user)):
    """
    Returns { url, s3_key } to allow frontend to upload directly to S3[cite: 77].
    Requires Authentication.
    """
    file_id = str(uuid.uuid4())
    # Organize files by user ID in S3
    s3_key = f"raw/{current_user.id}/{file_id}_{request.file_name}"
    
    try:
        url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key, 'ContentType': request.content_type},
            ExpiresIn=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"url": url, "s3_key": s3_key}

@app.post("/receipts")
def create_receipt_task(body: TaskRequest, current_user: User = Depends(get_current_user)):
    """
    Authenticated users upload a file and receive a task_id immediately[cite: 78].
    Triggers the Async Worker via SQS[cite: 25, 89].
    """
    task_id = str(uuid.uuid4())
    
    # 1. Write initial status 'PROCESSING' to DynamoDB [cite: 110]
    # We use user_id as partition key and receipt_id as sort key
    try:
        table.put_item(
            Item={
                'user_id': str(current_user.id),
                'receipt_id': task_id,
                's3_key': body.s3_key,
                'status': 'PROCESSING',
                'created_at': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")

    # 2. Push message to SQS queue to trigger Workers [cite: 25]
    if QUEUE_URL:
        message = {
            "task_id": task_id,
            "user_id": str(current_user.id),
            "s3_key": body.s3_key
        }
        try:
            sqs_client.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message)
            )
        except Exception as e:
            print(f"SQS Error: {e}")
            # Note: In production, handle this failure gracefully (e.g. rollback DB)
    
    return {"task_id": task_id, "status": "PROCESSING"}

handler = Mangum(app)