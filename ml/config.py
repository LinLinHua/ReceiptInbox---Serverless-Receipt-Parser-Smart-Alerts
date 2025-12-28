

import os
import logging
from typing import Optional

# AWS Configuration
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

# S3 Buckets
S3_BUCKET_RECEIPTS: Optional[str] = os.getenv("S3_BUCKET_RECEIPTS")
S3_BUCKET_TEXTRACT_OUTPUT: Optional[str] = os.getenv("S3_BUCKET_TEXTRACT_OUTPUT")

# SQS (for future use)
SQS_OCR_QUEUE_URL: Optional[str] = os.getenv("SQS_OCR_QUEUE_URL")

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

def get_logger(name: str) -> logging.Logger:
    
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    return logger

def validate_config() -> None:
    
    if not S3_BUCKET_RECEIPTS:
        raise ValueError("S3_BUCKET_RECEIPTS environment variable is required")
    
    if not S3_BUCKET_TEXTRACT_OUTPUT:
        raise ValueError("S3_BUCKET_TEXTRACT_OUTPUT environment variable is required")
