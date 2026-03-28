# ============================================================
# file_manager.py - Create folders, init JSON files safely
# ============================================================

import os
import json
import logging
from app.constants import (
    DATA_ROOT, DATA_DIR, BACKUP_DIR, INVOICES_PRINT, LOGS_DIR,
    SHOP_FILE, STOCK_FILE, VENDORS_FILE, CUSTOMERS_FILE,
    INVOICES_FILE, SETTINGS_FILE,
    DEFAULT_INVOICE_PREFIX, DEFAULT_TAX_PERCENT
)


# ─── Default Structures ─────────────────────────────────────
DEFAULT_STRUCTURES = {
    SHOP_FILE: {
        "shop_name": "",
        "owner_name": "",
        "address": "",
        "mobile": "",
        "gst_number": "",
        "email": "",
        "invoice_prefix": DEFAULT_INVOICE_PREFIX,
        "default_tax": DEFAULT_TAX_PERCENT,
        "printer": ""
    },
    STOCK_FILE:     [],
    VENDORS_FILE:   [],
    CUSTOMERS_FILE: [],
    INVOICES_FILE:  [],
    SETTINGS_FILE: {
        "invoice_prefix": DEFAULT_INVOICE_PREFIX,
        "default_tax": DEFAULT_TAX_PERCENT,
        "backup_folder": BACKUP_DIR,
        "last_invoice_number": 0
    }
}


def ensure_all_folders():
    """Create all required directories if they do not exist."""
    for folder in [DATA_ROOT, DATA_DIR, BACKUP_DIR, INVOICES_PRINT, LOGS_DIR]:
        os.makedirs(folder, exist_ok=True)


def ensure_all_files():
    """Create missing JSON files with default content."""
    for path, default in DEFAULT_STRUCTURES.items():
        if not os.path.exists(path):
            safe_write(path, default)


def is_first_run() -> bool:
    """Return True if shop_details.json is missing or shop_name is empty."""
    if not os.path.exists(SHOP_FILE):
        return True
    data = safe_read(SHOP_FILE)
    if isinstance(data, dict):
        return data.get("shop_name", "").strip() == ""
    return True


def safe_read(path: str):
    """Read a JSON file safely. Returns None on error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"File not found: {path}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Corrupted JSON: {path}. Resetting to default.")
        default = DEFAULT_STRUCTURES.get(path)
        if default is not None:
            safe_write(path, default)
        return default


def safe_write(path: str, data) -> bool:
    """Write data to a JSON file safely. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Failed to write {path}: {e}")
        return False


def initialize_app_storage():
    """Full initialization: create folders + files."""
    ensure_all_folders()
    ensure_all_files()
