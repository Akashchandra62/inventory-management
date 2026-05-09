# ============================================================
# file_manager.py - Folder creation + DB initialisation
# ============================================================

import os
import logging
from app.constants import (
    DATA_ROOT, DATA_DIR, BACKUP_DIR, INVOICES_PRINT, LOGS_DIR, ASSETS_DIR,
)


def ensure_all_folders():
    """Create all required directories if they do not exist."""
    for folder in [DATA_ROOT, DATA_DIR, BACKUP_DIR, INVOICES_PRINT, LOGS_DIR, ASSETS_DIR]:
        os.makedirs(folder, exist_ok=True)


def initialize_app_storage():
    """Full initialisation: create folders then init the SQLite database."""
    ensure_all_folders()
    from app.database import init_db
    init_db()


def is_first_run() -> bool:
    """Return True if shop_details has no shop_name set (fresh install)."""
    try:
        from app.database import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT shop_name FROM shop_details WHERE id = 1"
            ).fetchone()
        if row is None:
            return True
        return (row["shop_name"] or "").strip() == ""
    except Exception as e:
        logging.warning(f"is_first_run check failed: {e}")
        return True
