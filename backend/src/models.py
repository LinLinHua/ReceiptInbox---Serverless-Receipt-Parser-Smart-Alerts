import boto3
import json
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from botocore.exceptions import ClientError

# --- 1. Fetch Credentials from AWS Secrets Manager ---
def get_db_secret():
    secret_name = "prod/receiptinbox/db"
    region_name = "us-east-1" # Change to your region

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # Handle specific exceptions (e.g., resource not found, access denied)
        raise e

    # Parse the secret string JSON
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

# --- 2. Construct Connection String ---
# Only fetch secrets when initializing the app to avoid API costs on every import
try:
    db_creds = get_db_secret()
    
    # Format: postgresql://user:password@host:port/dbname
    SQLALCHEMY_DATABASE_URL = f"postgresql://{db_creds['username']}:{db_creds['password']}@{db_creds['host']}:{db_creds['port']}/{db_creds['dbname']}"
except Exception as e:
    print(f"Failed to fetch secrets: {e}")
    # Fallback for local testing if needed
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# --- 3. Setup SQLAlchemy ---
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- 4. Define Models ---
class User(Base):
    
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False) 
    created_at = Column(DateTime, default=datetime.utcnow)

# Helper to create tables (run this once)
def init_db():
    Base.metadata.create_all(bind=engine)