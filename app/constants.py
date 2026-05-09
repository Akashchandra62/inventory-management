# ============================================================
# constants.py - Paths, app metadata, credentials
# ============================================================

import os

# ─── Application Metadata ───────────────────────────────────
APP_NAME        = "Jewelry Billing System"
APP_VERSION     = "1.0.0"
APP_AUTHOR      = "Your Company"

# ─── Data Root (C Drive) ────────────────────────────────────
DATA_ROOT       = r"C:\JewelryBillingSystem"
DATA_DIR        = os.path.join(DATA_ROOT, "data")
BACKUP_DIR      = os.path.join(DATA_ROOT, "backups")
INVOICES_PRINT  = os.path.join(DATA_ROOT, "invoices_print")
LOGS_DIR        = os.path.join(DATA_ROOT, "logs")
ASSETS_DIR      = os.path.join(DATA_ROOT, "assets")

# ─── SQLite Database File ────────────────────────────────────
DB_FILE         = os.path.join(DATA_DIR, "jewelry.db")

# ─── Image Asset Paths ───────────────────────────────────────
LOGO_FILE        = os.path.join(ASSETS_DIR, "logo.png")
QR_FILE          = os.path.join(ASSETS_DIR, "qr_code.png")
CERTIFICATE_FILE = os.path.join(ASSETS_DIR, "certificate.png")

# ─── Hardcoded Login Credentials (fallback only) ─────────────
ADMIN_USERNAME  = "admin"
ADMIN_PASSWORD  = "jewelry@123"

# ─── Machine Authorization ──────────────────────────────────
ALLOWED_MACHINE_ID = "ANY"


def set_data_root(new_root: str):
    """
    Redirect every data path to a chosen profile folder.
    MUST be called before any service or config module is imported.
    Supports laptop profiles and external-drive (pendrive) profiles.
    """
    global DATA_ROOT, DATA_DIR, BACKUP_DIR, INVOICES_PRINT, LOGS_DIR, ASSETS_DIR
    global DB_FILE, LOGO_FILE, QR_FILE, CERTIFICATE_FILE

    DATA_ROOT      = new_root
    DATA_DIR       = os.path.join(DATA_ROOT, "data")
    BACKUP_DIR     = os.path.join(DATA_ROOT, "backups")
    INVOICES_PRINT = os.path.join(DATA_ROOT, "invoices_print")
    LOGS_DIR       = os.path.join(DATA_ROOT, "logs")
    ASSETS_DIR     = os.path.join(DATA_ROOT, "assets")

    DB_FILE          = os.path.join(DATA_DIR, "jewelry.db")
    LOGO_FILE        = os.path.join(ASSETS_DIR, "logo.png")
    QR_FILE          = os.path.join(ASSETS_DIR, "qr_code.png")
    CERTIFICATE_FILE = os.path.join(ASSETS_DIR, "certificate.png")


# ─── Invoice Settings ───────────────────────────────────────
DEFAULT_INVOICE_PREFIX  = "JB"
DEFAULT_TAX_PERCENT     = 3.0

# ─── UI Colors & Fonts ──────────────────────────────────────
COLOR_PRIMARY       = "#2c3e50"
COLOR_ACCENT        = "#f39c12"
COLOR_ACCENT2       = "#e67e22"
COLOR_BG            = "#f5f6fa"
COLOR_SIDEBAR       = "#2c3e50"
COLOR_SIDEBAR_TEXT  = "#ecf0f1"
COLOR_SIDEBAR_HOVER = "#34495e"
COLOR_WHITE         = "#ffffff"
COLOR_SUCCESS       = "#27ae60"
COLOR_DANGER        = "#e74c3c"
COLOR_INFO          = "#2980b9"
FONT_FAMILY         = "Segoe UI"
