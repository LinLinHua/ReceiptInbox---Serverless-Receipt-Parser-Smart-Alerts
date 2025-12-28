

import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from schemas import ParsedReceipt, ReceiptItem
from config import get_logger

logger = get_logger(__name__)

def parse_rekognition_response(
    job_id: str,
    user_id: str,
    rekognition_response: Dict[str, Any],
    rekognition_s3_key: str
) -> ParsedReceipt:
    
    logger.info(f"Parsing Rekognition response for job {job_id}")
    
    # Extract all text lines
    text_lines = extract_text_lines(rekognition_response)
    logger.debug(f"Extracted {len(text_lines)} text lines")
    
    # Extract merchant (usually first few lines)
    merchant = extract_merchant(text_lines)
    logger.info(f"Extracted merchant: {merchant}")
    
    # Extract date
    purchase_date = extract_date(text_lines)
    logger.info(f"Extracted date: {purchase_date}")
    
    # Extract line items
    items = extract_line_items(text_lines)
    logger.info(f"Extracted {len(items)} line items")
    
    # Extract totals from text
    subtotal, tax, total = extract_totals(text_lines)
    
    # If total not found, calculate from items
    if total is None and items:
        calculated_total = sum(item.line_total for item in items)
        logger.info(f"Total not found in text, calculated from items: ${calculated_total:.2f}")
        total = calculated_total
        # Estimate subtotal and tax if not found
        if subtotal is None:
            subtotal = total  # Assume no tax if we can't find it
        if tax is None:
            tax = 0.0
    
    logger.info(f"Final totals - Subtotal: {subtotal}, Tax: {tax}, Total: {total}")
    
    # Create ParsedReceipt
    receipt = ParsedReceipt(
        job_id=job_id,
        user_id=user_id,
        merchant=merchant,
        purchase_date=purchase_date,
        subtotal=subtotal,
        tax=tax,
        total=total,
        currency="USD",
        items=items,
        raw_textract_s3_key=rekognition_s3_key
    )
    
    return receipt

def extract_text_lines(rekognition_response: Dict[str, Any]) -> List[str]:
    """Extract all LINE text from Rekognition response."""
    text_detections = rekognition_response.get('TextDetections', [])
    lines = [
        t.get('DetectedText', '').strip()
        for t in text_detections
        if t.get('Type') == 'LINE' and t.get('DetectedText')
    ]
    return lines

def extract_merchant(text_lines: List[str]) -> Optional[str]:
    
    if not text_lines:
        return None
    
    # Check first 5 lines for merchant
    candidates = text_lines[:5]
    
    # Filter out lines that look like addresses, dates, or numbers
    filtered = []
    for line in candidates:
        # Skip if mostly numbers
        if sum(c.isdigit() for c in line) > len(line) * 0.5:
            continue
        # Skip if looks like address (has numbers at start)
        if re.match(r'^\d+\s', line):
            continue
        # Skip if looks like date
        if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line):
            continue
        filtered.append(line)
    
    # Return first filtered line or first line as fallback
    return filtered[0] if filtered else (text_lines[0] if text_lines else None)

def extract_date(text_lines: List[str]) -> Optional[str]:
    
    date_patterns = [
        # Standard date formats
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # MM/DD/YYYY or DD-MM-YYYY
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2})',  # MM/DD/YY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # YYYY-MM-DD
        r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',  # Month DD, YYYY
        # Time stamps with dates
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+\d{1,2}:\d{2}',  # MM/DD/YYYY HH:MM
    ]
    
    for line in text_lines:
        for pattern in date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Try to parse and normalize
                try:
                    # Try various formats
                    formats = [
                        '%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%m-%d-%y',
                        '%Y-%m-%d', '%Y/%m/%d',
                        '%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y',
                        '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y'
                    ]
                    for fmt in formats:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            return dt.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except Exception:
                    pass
                # Return as-is if can't parse
                return date_str
    
    # If no date found, return today's date as fallback
    return datetime.now().strftime('%Y-%m-%d')

def extract_line_items(text_lines: List[str]) -> List[ReceiptItem]:
    
    items = []
    
    # Pattern for standalone price (just a number)
    price_pattern = r'^\$?(\d+\.\d{2})$'
    
    # Keywords to skip (totals, headers, etc.)
    skip_keywords = ['TOTAL', 'SUBTOTAL', 'TAX', 'BALANCE', 'CHANGE', 'CASH', 'CREDIT', 'DEBIT']
    
    i = 0
    while i < len(text_lines):
        line = text_lines[i].strip()
        
        # Check if this line is a price
        match = re.match(price_pattern, line)
        if match:
            price_str = match.group(1)
            
            try:
                price = float(price_str)
                
                # Look backwards for description (previous 1-3 lines)
                description = None
                for j in range(1, min(4, i + 1)):
                    prev_line = text_lines[i - j].strip()
                    
                    # Skip if it's another price
                    if re.match(price_pattern, prev_line):
                        continue
                    
                    # Skip if it contains skip keywords
                    if any(kw in prev_line.upper() for kw in skip_keywords):
                        continue
                    
                    # Skip very short lines or numbers-only
                    if len(prev_line) < 3 or prev_line.isdigit():
                        continue
                    
                    # This looks like a description!
                    description = prev_line
                    break
                
                # If we found a description, add the item
                if description and 0 < price < 10000:
                    # Clean up description
                    # Remove quantity prefixes (e.g., "2EA", "12EA")
                    description = re.sub(r'^\d+EA\s*', '', description)
                    # Remove @ price indicators
                    description = re.sub(r'\s*@\s*\d+\.\d{2}/EA$', '', description)
                    
                    items.append(ReceiptItem(
                        description=description,
                        line_total=price
                    ))
                    
            except ValueError:
                pass
        
        i += 1
    
    return items

def extract_totals(text_lines: List[str]) -> tuple[Optional[float], Optional[float], Optional[float]]:
    
    subtotal = None
    tax = None
    total = None
    
    # Patterns for totals
    subtotal_pattern = r'(?:SUB\s*TOTAL|SUBTOTAL)\s*\$?(\d+\.\d{2})'
    tax_pattern = r'(?:TAX|SALES\s*TAX)\s*\$?(\d+\.\d{2})'
    total_pattern = r'(?:^TOTAL|GRAND\s*TOTAL|AMOUNT\s*DUE)\s*\$?(\d+\.\d{2})'
    
    for line in text_lines:
        line_upper = line.upper()
        
        # Extract subtotal
        if not subtotal:
            match = re.search(subtotal_pattern, line_upper)
            if match:
                try:
                    subtotal = float(match.group(1))
                except ValueError:
                    pass
        
        # Extract tax
        if not tax:
            match = re.search(tax_pattern, line_upper)
            if match:
                try:
                    tax = float(match.group(1))
                except ValueError:
                    pass
        
        # Extract total
        if not total:
            match = re.search(total_pattern, line_upper)
            if match:
                try:
                    total = float(match.group(1))
                except ValueError:
                    pass
    
    return subtotal, tax, total
