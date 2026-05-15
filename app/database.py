# ============================================================
# app/database.py  —  SQLite connection manager & schema
# ============================================================
import sqlite3
import logging
from contextlib import contextmanager


def _db_path() -> str:
    from app import constants
    return constants.DB_FILE


@contextmanager
def get_db():
    """Yield a SQLite connection that auto-commits on success or rolls back on error."""
    path = _db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Schema ──────────────────────────────────────────────────
_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS shop_details (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    shop_name      TEXT    DEFAULT '',
    owner_name     TEXT    DEFAULT '',
    address        TEXT    DEFAULT '',
    mobile         TEXT    DEFAULT '',
    gst_number     TEXT    DEFAULT '',
    email          TEXT    DEFAULT '',
    invoice_prefix TEXT    DEFAULT 'JB',
    default_tax    REAL    DEFAULT 3.0,
    printer        TEXT    DEFAULT '',
    categories     TEXT    DEFAULT 'Gold,Silver,Diamond,Platinum,Gemstone,Other',
    item_groups    TEXT    DEFAULT '',
    extra_json     TEXT    DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    customer_name TEXT DEFAULT '',
    mobile        TEXT DEFAULT '',
    address       TEXT DEFAULT '',
    email         TEXT DEFAULT '',
    aadhaar       TEXT DEFAULT '',
    pan           TEXT DEFAULT '',
    gst_number    TEXT DEFAULT '',
    notes         TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS vendors (
    vendor_id   TEXT PRIMARY KEY,
    vendor_name TEXT DEFAULT '',
    phone       TEXT DEFAULT '',
    address     TEXT DEFAULT '',
    gst_number  TEXT DEFAULT '',
    email       TEXT DEFAULT '',
    notes       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id       TEXT PRIMARY KEY,
    invoice_number   TEXT UNIQUE NOT NULL,
    date             TEXT NOT NULL,
    time             TEXT DEFAULT '',
    customer_name    TEXT DEFAULT '',
    customer_mobile  TEXT DEFAULT '',
    customer_address TEXT DEFAULT '',
    customer_email   TEXT DEFAULT '',
    customer_gst     TEXT DEFAULT '',
    customer_aadhaar TEXT DEFAULT '',
    customer_pan     TEXT DEFAULT '',
    subtotal         REAL DEFAULT 0.0,
    tax_percent      REAL DEFAULT 3.0,
    cgst_percent     REAL DEFAULT 1.5,
    sgst_percent     REAL DEFAULT 1.5,
    igst_percent     REAL DEFAULT 0.0,
    cgst_amount      REAL DEFAULT 0.0,
    sgst_amount      REAL DEFAULT 0.0,
    igst_amount      REAL DEFAULT 0.0,
    tax_amount       REAL DEFAULT 0.0,
    grand_total      REAL DEFAULT 0.0,
    cash_paid        REAL DEFAULT 0.0,
    card_paid        REAL DEFAULT 0.0,
    card_details     TEXT DEFAULT '',
    cheque_paid      REAL DEFAULT 0.0,
    cheque_details   TEXT DEFAULT '',
    upi_paid         REAL DEFAULT 0.0,
    old_purchase     REAL DEFAULT 0.0,
    advance_paid     REAL DEFAULT 0.0,
    round_off        REAL DEFAULT 0.0,
    due_amount       REAL DEFAULT 0.0,
    due_date         TEXT DEFAULT '',
    refund_amount    REAL DEFAULT 0.0,
    refund_mode      TEXT DEFAULT '',
    remarks          TEXT DEFAULT '',
    notes            TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id    TEXT    NOT NULL,
    name          TEXT    DEFAULT '',
    category      TEXT    DEFAULT '',
    tag           TEXT    DEFAULT '',
    huid          TEXT    DEFAULT '',
    hsn_code      TEXT    DEFAULT '7113',
    purity        TEXT    DEFAULT '',
    quantity      INTEGER DEFAULT 1,
    weight        REAL    DEFAULT 0.0,
    less_weight   REAL    DEFAULT 0.0,
    nett_weight   REAL    DEFAULT 0.0,
    rate          REAL    DEFAULT 0.0,
    making_charge REAL    DEFAULT 0.0,
    making_pct    REAL    DEFAULT 0.0,
    stone_charge  REAL    DEFAULT 0.0,
    discount      REAL    DEFAULT 0.0,
    total         REAL    DEFAULT 0.0,
    metal         TEXT    DEFAULT '',
    metal_id      TEXT    DEFAULT '',
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock (
    item_id        TEXT PRIMARY KEY,
    item_name      TEXT    DEFAULT '',
    category       TEXT    DEFAULT '',
    purity         TEXT    DEFAULT '',
    gross_weight   REAL    DEFAULT 0.0,
    net_weight     REAL    DEFAULT 0.0,
    quantity       INTEGER DEFAULT 0,
    purchase_price REAL    DEFAULT 0.0,
    selling_price  REAL    DEFAULT 0.0,
    vendor_name    TEXT    DEFAULT '',
    remarks        TEXT    DEFAULT '',
    custom_data    TEXT    DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS stock_entries (
    entry_id     TEXT PRIMARY KEY,
    entry_type   TEXT    DEFAULT 'IN',
    source       TEXT    DEFAULT '',
    voucher_no   TEXT    DEFAULT '',
    voucher_date TEXT    DEFAULT '',
    metal_type   TEXT    DEFAULT '',
    item_name    TEXT    DEFAULT '',
    sub_name     TEXT    DEFAULT '',
    purity       TEXT    DEFAULT '',
    dabba_name   TEXT    DEFAULT '',
    dabba_wt     REAL    DEFAULT 0.0,
    gross_wt     REAL    DEFAULT 0.0,
    plastic_wt   REAL    DEFAULT 0.0,
    qty_in       INTEGER DEFAULT 0,
    less_wt      REAL    DEFAULT 0.0,
    dia_wt       REAL    DEFAULT 0.0,
    net_wt       REAL    DEFAULT 0.0,
    location     TEXT    DEFAULT '',
    out_gross_wt REAL    DEFAULT 0.0,
    out_less_wt  REAL    DEFAULT 0.0,
    out_net_wt   REAL    DEFAULT 0.0,
    qty_out      INTEGER DEFAULT 0,
    remarks      TEXT    DEFAULT '',
    invoice_id   TEXT    DEFAULT '',
    rate         REAL    DEFAULT 0.0,
    amount       REAL    DEFAULT 0.0,
    vendor_name  TEXT    DEFAULT '',
    description  TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS metals (
    metal_id TEXT PRIMARY KEY,
    name     TEXT DEFAULT '',
    purity   TEXT DEFAULT '',
    rate     REAL DEFAULT 0.0,
    labour   REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS item_catalog (
    catalog_id TEXT PRIMARY KEY,
    name       TEXT UNIQUE NOT NULL DEFAULT '',
    code       TEXT DEFAULT '',
    category   TEXT DEFAULT '',
    purity     TEXT DEFAULT '',
    item_group TEXT DEFAULT '',
    metal_id   TEXT DEFAULT '',
    rate       REAL DEFAULT 0.0,
    labour     REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS karigar_profiles (
    karigar_id TEXT PRIMARY KEY,
    name       TEXT DEFAULT '',
    mobile     TEXT DEFAULT '',
    email      TEXT DEFAULT '',
    address    TEXT DEFAULT '',
    pan        TEXT DEFAULT '',
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS karigar_transactions (
    transaction_id     TEXT PRIMARY KEY,
    tx_type            TEXT DEFAULT 'TAKE',
    memo_no            TEXT DEFAULT '',
    karigar_name       TEXT DEFAULT '',
    karigar_mobile     TEXT DEFAULT '',
    date               TEXT DEFAULT '',
    created_at         TEXT DEFAULT '',
    total_fine_gold    REAL DEFAULT 0.0,
    total_payment      REAL DEFAULT 0.0,
    items_json         TEXT DEFAULT '[]',
    give_gold_gross_wt REAL DEFAULT 0.0,
    give_gold_less_wt  REAL DEFAULT 0.0,
    give_gold_net_wt   REAL DEFAULT 0.0,
    give_gold_tounch   REAL DEFAULT 0.0,
    give_gold_fine     REAL DEFAULT 0.0,
    give_cash          REAL DEFAULT 0.0,
    give_rate_10g      REAL DEFAULT 0.0,
    give_cash_fine     REAL DEFAULT 0.0,
    remarks            TEXT DEFAULT ''
);
"""


def _migrate(conn: sqlite3.Connection):
    """Add columns introduced after the initial release (safe to run on every startup)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(customers)")}
    for col, defn in (
        ("aadhaar",    "TEXT DEFAULT ''"),
        ("pan",        "TEXT DEFAULT ''"),
        ("gst_number", "TEXT DEFAULT ''"),
    ):
        if col not in existing:
            conn.execute(f"ALTER TABLE customers ADD COLUMN {col} {defn}")

    existing_se = {row[1] for row in conn.execute("PRAGMA table_info(stock_entries)")}
    if "out_less_wt" not in existing_se:
        conn.execute("ALTER TABLE stock_entries ADD COLUMN out_less_wt REAL DEFAULT 0.0")

    # ── Customer uniqueness by mobile ──────────────────────────────────────
    # Before adding the unique index, collapse any existing duplicate mobile records:
    # keep the most-complete entry, delete the rest.
    dup_rows = conn.execute(
        "SELECT mobile FROM customers WHERE mobile != '' "
        "GROUP BY mobile HAVING COUNT(*) > 1"
    ).fetchall()
    for dup_row in dup_rows:
        mob = dup_row[0]
        candidates = conn.execute(
            "SELECT customer_id, customer_name, address, email, aadhaar, pan "
            "FROM customers WHERE mobile = ?", (mob,)
        ).fetchall()
        # Score each candidate by number of non-empty fields
        def _score(r):
            return sum(1 for f in ("customer_name", "address", "email", "aadhaar", "pan") if r[f])
        ranked = sorted(candidates, key=_score, reverse=True)
        for loser in ranked[1:]:
            conn.execute("DELETE FROM customers WHERE customer_id = ?", (loser["customer_id"],))

    # Partial unique index: enforces one record per non-empty mobile number.
    # Walk-in customers with no mobile can still coexist.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_mobile "
        "ON customers(mobile) WHERE mobile != ''"
    )


def init_db():
    """Create all tables and seed default rows (idempotent — safe to call on every startup)."""
    with get_db() as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)
        _seed_defaults(conn)
    logging.info("Database initialised.")


def _seed_defaults(conn: sqlite3.Connection):
    conn.execute("INSERT OR IGNORE INTO shop_details (id) VALUES (1)")
    conn.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        [
            ("last_invoice_number", "0"),
            ("username",            "admin"),
            ("password",            "jewelry@123"),
            ("stock_custom_columns","[]"),
        ]
    )
