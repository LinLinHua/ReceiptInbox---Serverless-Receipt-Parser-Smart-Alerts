"""
ML Receipt Processing Stack

This package provides OCR, parsing, categorization, and anomaly detection
for receipt images using AWS Textract.

Main components:
- ocr_textract: AWS Textract integration
- parse_receipt: Convert OCR output to structured data
- categorize: Rule-based receipt categorization
- anomalies: Anomaly detection
- lambda_handler: AWS Lambda entry point

For local testing, see tests/test_local_pipeline.py
"""

from schemas import (
    ReceiptItem,
    ParsedReceipt,
    AlertEvent,
    MLResult,
    ReceiptJobEvent
)
from lambda_handler import handler

__version__ = "0.1.0"

__all__ = [
    "ReceiptItem",
    "ParsedReceipt",
    "AlertEvent",
    "MLResult",
    "ReceiptJobEvent",
    "handler",
]
