# ============================================================
# utils.py - Shared utility functions
# ============================================================

import re
import uuid
from datetime import datetime


def generate_invoice_number(prefix: str, last_number: int) -> str:
    """Generate next invoice number like JB-0042."""
    next_num = last_number + 1
    return f"{prefix}-{next_num:04d}", next_num


def current_datetime_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def format_currency(amount: float) -> str:
    """Format number as Indian Rupees string."""
    try:
        return f"₹ {float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹ 0.00"


def validate_mobile(mobile: str) -> bool:
    """Simple 10-digit Indian mobile validation."""
    return bool(re.match(r"^[6-9]\d{9}$", mobile.strip()))


def validate_gst(gst: str) -> bool:
    """Basic GST number format check (15 chars alphanumeric)."""
    return bool(re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gst.strip()))


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def unique_id() -> str:
    return str(uuid.uuid4())[:8].upper()
