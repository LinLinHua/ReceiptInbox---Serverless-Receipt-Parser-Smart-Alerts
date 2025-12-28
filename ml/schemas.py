

from typing import Optional
from pydantic import BaseModel, Field

class ReceiptItem(BaseModel):
    """Individual line item on a receipt."""
    
    description: str = Field(..., description="Item description/name")
    qty: Optional[float] = Field(None, description="Quantity purchased")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    line_total: Optional[float] = Field(None, description="Total for this line item")
    category: Optional[str] = Field(None, description="Predicted category")
    category_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score for category prediction")

class ParsedReceipt(BaseModel):
    """Structured receipt data extracted from OCR."""
    
    job_id: str = Field(..., description="Unique job identifier")
    user_id: str = Field(..., description="User who uploaded the receipt")
    merchant: Optional[str] = Field(None, description="Merchant/store name")
    purchase_date: Optional[str] = Field(None, description="Purchase date (ISO format)")
    subtotal: Optional[float] = Field(None, description="Subtotal amount")
    tax: Optional[float] = Field(None, description="Tax amount")
    total: Optional[float] = Field(None, description="Total amount")
    currency: Optional[str] = Field(None, description="Currency code (e.g., USD)")
    items: list[ReceiptItem] = Field(default_factory=list, description="List of line items")
    raw_textract_s3_key: Optional[str] = Field(None, description="S3 key for raw Textract output")

class AlertEvent(BaseModel):
    """Anomaly or alert notification."""
    
    type: str = Field(..., description="Alert type (e.g., HIGH_TOTAL, DUPLICATE, POSSIBLE_ERROR)")
    message: str = Field(..., description="Human-readable alert message")

class MLResult(BaseModel):
    """Final output from the ML pipeline."""
    
    parsed_receipt: ParsedReceipt = Field(..., description="Structured receipt data")
    alerts: list[AlertEvent] = Field(default_factory=list, description="List of alerts/anomalies detected")

class ReceiptJobEvent(BaseModel):
    """Lambda input event schema."""
    
    job_id: str = Field(..., description="Unique job identifier")
    user_id: str = Field(..., description="User who uploaded the receipt")
    s3_key: str = Field(..., description="S3 key for the uploaded receipt image")
