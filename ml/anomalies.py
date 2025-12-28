"""Anomaly detection for receipt processing."""

from typing import Optional

from schemas import ParsedReceipt, AlertEvent
from config import get_logger

logger = get_logger(__name__)

DEFAULT_HIGH_TOTAL_THRESHOLD = 200.0
TOTAL_CONSISTENCY_TOLERANCE = 0.05  # 5% tolerance


def detect_anomalies(
    parsed: ParsedReceipt,
    high_total_threshold: float = DEFAULT_HIGH_TOTAL_THRESHOLD
) -> list[AlertEvent]:
    """Detect anomalies: high total, inconsistency, duplicates."""
    logger.info(f"Running anomaly detection for job {parsed.job_id}")
    
    alerts = []
    
    high_total_alert = _check_high_total(parsed, high_total_threshold)
    if high_total_alert:
        alerts.append(high_total_alert)
    
    consistency_alert = _check_total_consistency(parsed)
    if consistency_alert:
        alerts.append(consistency_alert)
    
    duplicate_alert = _check_duplicate_receipt(parsed)
    if duplicate_alert:
        alerts.append(duplicate_alert)
    logger.info(f"Detected {len(alerts)} anomalies")
    return alerts


def _check_high_total(parsed: ParsedReceipt, threshold: float) -> Optional[AlertEvent]:
    if parsed.total is None:
        return None
    
    if parsed.total > threshold:
        logger.warning(f"High total detected: ${parsed.total:.2f} (threshold: ${threshold:.2f})")
        return AlertEvent(
            type="HIGH_TOTAL",
            message=f"Receipt total ${parsed.total:.2f} exceeds threshold of ${threshold:.2f}"
        )
    
    return None


def _check_total_consistency(parsed: ParsedReceipt) -> Optional[AlertEvent]:
    if parsed.subtotal is None or parsed.tax is None or parsed.total is None:
        return None
    
    expected_total = parsed.subtotal + parsed.tax
    difference = abs(expected_total - parsed.total)
    tolerance = parsed.total * TOTAL_CONSISTENCY_TOLERANCE
    
    if difference > tolerance:
        logger.warning(
            f"Total inconsistency detected: "
            f"subtotal ${parsed.subtotal:.2f} + tax ${parsed.tax:.2f} = ${expected_total:.2f}, "
            f"but total is ${parsed.total:.2f} (difference: ${difference:.2f})"
        )
        return AlertEvent(
            type="POSSIBLE_ERROR",
            message=(
                f"Subtotal (${parsed.subtotal:.2f}) + Tax (${parsed.tax:.2f}) = "
                f"${expected_total:.2f}, but receipt shows total of ${parsed.total:.2f}. "
                f"Difference: ${difference:.2f}"
            )
        )
    


_RECEIPT_CACHE: dict[str, ParsedReceipt] = {}


def _check_duplicate_receipt(parsed: ParsedReceipt) -> Optional[AlertEvent]:
    import hashlib
    
    hash_components = [
        parsed.merchant or "UNKNOWN",
        parsed.purchase_date or "NO_DATE",
        f"{parsed.total:.2f}" if parsed.total else "0.00",
        str(len(parsed.items))
    ]
    
    hash_string = "|".join(hash_components)
    receipt_hash = hashlib.md5(hash_string.encode()).hexdigest()
    
    # Check if we've seen this receipt before
    if receipt_hash in _RECEIPT_CACHE:
        previous = _RECEIPT_CACHE[receipt_hash]
        logger.warning(
            f"Duplicate receipt detected: "
            f"merchant={parsed.merchant}, date={parsed.purchase_date}, total=${parsed.total:.2f}"
        )
        return AlertEvent(
            type="DUPLICATE_RECEIPT",
            message=(
                f"This receipt appears to be a duplicate. "
                f"Previous submission: {previous.merchant} on {previous.purchase_date} "
                f"for ${previous.total:.2f}"
            )
        )
    
    # Store this receipt in cache
    _RECEIPT_CACHE[receipt_hash] = parsed
    
    return None


def clear_receipt_cache():
    global _RECEIPT_CACHE
    _RECEIPT_CACHE = {}
