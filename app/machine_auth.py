# app/machine_auth.py - Single-PC machine lock
from typing import Tuple
import hashlib
import subprocess
import sys
import os


def _run(cmd):
    """Run a shell command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_motherboard_serial() -> str:
    out = _run(["wmic", "baseboard", "get", "SerialNumber"])
    lines = [l.strip() for l in out.splitlines() if l.strip() and l.strip().lower() != "serialnumber"]
    return lines[0] if lines else "UNKNOWN_MB"


def get_disk_serial() -> str:
    out = _run(["wmic", "diskdrive", "get", "SerialNumber"])
    lines = [l.strip() for l in out.splitlines() if l.strip() and l.strip().lower() != "serialnumber"]
    return lines[0] if lines else "UNKNOWN_DISK"


def get_machine_guid() -> str:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography"
        )
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return guid
    except Exception:
        return "UNKNOWN_GUID"


def build_machine_fingerprint() -> str:
    parts = [
        get_motherboard_serial(),
        get_disk_serial(),
        get_machine_guid(),
    ]
    combined = "|".join(parts)
    fingerprint = hashlib.sha256(combined.encode()).hexdigest()[:24].upper()
    return fingerprint


def is_authorized() -> Tuple[bool, str]:
    from app.constants import ALLOWED_MACHINE_ID
    fp = build_machine_fingerprint()

    if ALLOWED_MACHINE_ID == "ANY":
        return True, fp

    if fp == ALLOWED_MACHINE_ID:
        return True, fp

    return False, fp


if __name__ == "__main__":
    fp = build_machine_fingerprint()
    print("=" * 50)
    print("  Your Machine Fingerprint:")
    print(f"  {fp}")
    print("=" * 50)
    print("Paste this into app/constants.py as ALLOWED_MACHINE_ID")
    input("\nPress Enter to exit...")
