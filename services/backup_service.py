# services/backup_service.py
from typing import Tuple
import os
import shutil
from datetime import datetime


def backup_all(destination_folder: str) -> Tuple[bool, str]:
    """Copy entire data folder to destination. Returns (success, message)."""
    from app.constants import DATA_DIR
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = os.path.join(destination_folder, f"JBS_Backup_{ts}")
        shutil.copytree(DATA_DIR, target)
        return True, f"Backup saved to:\n{target}"
    except Exception as e:
        return False, f"Backup failed: {e}"


def restore_backup(backup_folder: str) -> Tuple[bool, str]:
    """Replace current data folder with backup. Returns (success, message)."""
    from app.constants import DATA_DIR
    try:
        if not os.path.isdir(backup_folder):
            return False, "Selected folder is not valid."
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        old = DATA_DIR + f"_old_{ts}"
        os.rename(DATA_DIR, old)
        shutil.copytree(backup_folder, DATA_DIR)
        return True, f"Restore successful! Old data saved as:\n{old}"
    except Exception as e:
        return False, f"Restore failed: {e}"
