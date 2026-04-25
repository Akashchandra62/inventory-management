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
ASSETS_DIR      = os.path.join(DATA_ROOT, "assets")   # ← logo, QR stored here

# ─── JSON File Paths ────────────────────────────────────────
SHOP_FILE       = os.path.join(DATA_DIR, "shop_details.json")
STOCK_FILE          = os.path.join(DATA_DIR, "stock.json")
ITEMS_CATALOG_FILE  = os.path.join(DATA_DIR, "item_catalog.json")
METALS_FILE         = os.path.join(DATA_DIR, "metals.json")
VENDORS_FILE        = os.path.join(DATA_DIR, "vendors.json")
CUSTOMERS_FILE  = os.path.join(DATA_DIR, "customers.json")
INVOICES_FILE   = os.path.join(DATA_DIR, "invoices.json")
SETTINGS_FILE   = os.path.join(DATA_DIR, "settings.json")

# ─── Image Asset Paths ───────────────────────────────────────
LOGO_FILE        = os.path.join(ASSETS_DIR, "logo.png")          # shop logo (left header)
QR_FILE          = os.path.join(ASSETS_DIR, "qr_code.png")       # payment QR image
CERTIFICATE_FILE = os.path.join(ASSETS_DIR, "certificate.png")   # hallmark / certificate (right header)

# ─── Hardcoded Login Credentials ────────────────────────────
ADMIN_USERNAME  = "admin"
ADMIN_PASSWORD  = "jewelry@123"

# ─── Machine Authorization ──────────────────────────────────
ALLOWED_MACHINE_ID = "ANY"

def set_data_root(new_root: str):
    """
    Redirect every data path to a chosen profile folder.
    MUST be called before file_manager / config / any service is imported.
    """
    global DATA_ROOT, DATA_DIR, BACKUP_DIR, INVOICES_PRINT, LOGS_DIR, ASSETS_DIR
    global SHOP_FILE, STOCK_FILE, ITEMS_CATALOG_FILE, VENDORS_FILE
    global CUSTOMERS_FILE, INVOICES_FILE, SETTINGS_FILE, LOGO_FILE, QR_FILE, METALS_FILE

    DATA_ROOT      = new_root
    DATA_DIR       = os.path.join(DATA_ROOT, "data")
    BACKUP_DIR     = os.path.join(DATA_ROOT, "backups")
    INVOICES_PRINT = os.path.join(DATA_ROOT, "invoices_print")
    LOGS_DIR       = os.path.join(DATA_ROOT, "logs")
    ASSETS_DIR     = os.path.join(DATA_ROOT, "assets")

    SHOP_FILE          = os.path.join(DATA_DIR, "shop_details.json")
    STOCK_FILE         = os.path.join(DATA_DIR, "stock.json")
    ITEMS_CATALOG_FILE = os.path.join(DATA_DIR, "item_catalog.json")
    METALS_FILE        = os.path.join(DATA_DIR, "metals.json")
    VENDORS_FILE       = os.path.join(DATA_DIR, "vendors.json")
    CUSTOMERS_FILE     = os.path.join(DATA_DIR, "customers.json")
    INVOICES_FILE      = os.path.join(DATA_DIR, "invoices.json")
    SETTINGS_FILE      = os.path.join(DATA_DIR, "settings.json")

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