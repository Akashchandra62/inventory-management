# services/backup_service.py
import os
import shutil
from datetime import datetime
from typing import Tuple


def backup_all(destination_folder: str) -> Tuple[bool, str]:
    """Copy the database file (and assets) to a timestamped backup folder."""
    from app.constants import DB_FILE, ASSETS_DIR, DATA_ROOT
    try:
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(destination_folder, f"JBS_Backup_{ts}")
        os.makedirs(target, exist_ok=True)

        # Copy database
        if os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, os.path.join(target, "jewelry.db"))

        # Copy assets (logo, QR, certificate)
        if os.path.isdir(ASSETS_DIR):
            dest_assets = os.path.join(target, "assets")
            if os.path.exists(dest_assets):
                shutil.rmtree(dest_assets)
            shutil.copytree(ASSETS_DIR, dest_assets)

        return True, f"Backup saved to:\n{target}"
    except Exception as e:
        return False, f"Backup failed: {e}"


def restore_backup(backup_folder: str) -> Tuple[bool, str]:
    """Restore database from a backup folder, preserving the old DB as a safety copy."""
    from app.constants import DB_FILE, ASSETS_DIR, DATA_ROOT
    try:
        backup_db = os.path.join(backup_folder, "jewelry.db")
        if not os.path.isfile(backup_db):
            return False, "No jewelry.db found in the selected backup folder."

        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        old_db = DB_FILE + f"_old_{ts}"

        # Move current DB aside as a safety copy
        if os.path.exists(DB_FILE):
            os.rename(DB_FILE, old_db)

        shutil.copy2(backup_db, DB_FILE)

        # Restore assets if present in backup
        backup_assets = os.path.join(backup_folder, "assets")
        if os.path.isdir(backup_assets):
            if os.path.exists(ASSETS_DIR):
                shutil.rmtree(ASSETS_DIR)
            shutil.copytree(backup_assets, ASSETS_DIR)

        return True, f"Restore successful!\nOld database saved as:\n{old_db}"
    except Exception as e:
        return False, f"Restore failed: {e}"
