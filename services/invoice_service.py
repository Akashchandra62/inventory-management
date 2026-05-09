# services/invoice_service.py
from typing import Optional
from datetime import datetime

from app.config import AppConfig
from app.utils import unique_id, current_date_str
from services.customer_service import find_or_create_customer

# ── Column sets ───────────────────────────────────────────────
_INV_HEADER_COLS = (
    "invoice_id", "invoice_number", "date", "time",
    "customer_name", "customer_mobile", "customer_address",
    "customer_email", "customer_gst", "customer_aadhaar", "customer_pan",
    "subtotal", "tax_percent", "cgst_percent", "sgst_percent", "igst_percent",
    "cgst_amount", "sgst_amount", "igst_amount", "tax_amount", "grand_total",
    "cash_paid", "card_paid", "card_details", "cheque_paid", "cheque_details",
    "upi_paid", "old_purchase", "advance_paid", "round_off",
    "due_amount", "due_date", "refund_amount", "refund_mode",
    "remarks", "notes",
)

_ITEM_COLS = (
    "invoice_id", "name", "category", "tag", "huid", "hsn_code",
    "purity", "quantity", "weight", "less_weight", "nett_weight",
    "rate", "making_charge", "making_pct", "stone_charge",
    "discount", "total", "metal", "metal_id",
)

_ENTRY_COLS = (
    "entry_id", "entry_type", "source", "voucher_no", "voucher_date",
    "metal_type", "item_name", "sub_name", "purity",
    "dabba_name", "dabba_wt", "gross_wt", "plastic_wt",
    "qty_in", "less_wt", "dia_wt", "net_wt", "location",
    "out_gross_wt", "out_net_wt", "qty_out", "remarks",
)


# ── Helpers ───────────────────────────────────────────────────

def _inv_row_to_dict(inv_row, item_rows) -> dict:
    d = dict(inv_row)
    d["items"] = [dict(r) for r in item_rows]
    return d


def _insert_header(conn, inv: dict):
    vals = tuple(inv.get(c, "") for c in _INV_HEADER_COLS)
    cols = ", ".join(_INV_HEADER_COLS)
    ph   = ", ".join("?" * len(_INV_HEADER_COLS))
    conn.execute(f"INSERT INTO invoices ({cols}) VALUES ({ph})", vals)


def _insert_items(conn, invoice_id: str, items: list):
    for item in items:
        vals = tuple(
            invoice_id if c == "invoice_id" else item.get(c, "")
            for c in _ITEM_COLS
        )
        cols = ", ".join(_ITEM_COLS)
        ph   = ", ".join("?" * len(_ITEM_COLS))
        conn.execute(f"INSERT INTO invoice_items ({cols}) VALUES ({ph})", vals)


def _insert_stock_out(conn, item: dict, inv_number: str, date_str: str, customer_name: str):
    vals = (
        unique_id(),            # entry_id
        "OUT",                  # entry_type
        "invoice",              # source
        inv_number,             # voucher_no
        date_str,               # voucher_date
        item.get("metal",  ""), # metal_type
        item.get("name",   ""), # item_name
        "",                     # sub_name
        item.get("purity", ""), # purity
        "", 0.0, 0.0, 0.0,      # dabba_name, dabba_wt, gross_wt, plastic_wt
        0,                      # qty_in
        0.0, 0.0, 0.0,          # less_wt, dia_wt, net_wt
        "OUT",                  # location
        float(item.get("weight",      0)),  # out_gross_wt
        float(item.get("nett_weight", 0)),  # out_net_wt
        int(item.get("quantity", 1)),       # qty_out
        f"Invoice {inv_number} — {customer_name}",  # remarks
    )
    conn.execute(
        f"INSERT INTO stock_entries ({', '.join(_ENTRY_COLS)}) VALUES ({', '.join('?' * len(_ENTRY_COLS))})",
        vals,
    )


def _reduce_stock(conn, item_name: str, quantity: int, purity: str = ""):
    conn.execute(
        """UPDATE stock
           SET quantity = MAX(0, quantity - ?)
           WHERE item_id = (
               SELECT item_id FROM stock
               WHERE LOWER(item_name) = LOWER(?)
                 AND (? = '' OR LOWER(purity) = LOWER(?))
               LIMIT 1
           )""",
        (quantity, item_name, purity, purity),
    )


def _restore_stock(conn, item_name: str, quantity: int, purity: str = ""):
    conn.execute(
        """UPDATE stock
           SET quantity = quantity + ?
           WHERE item_id = (
               SELECT item_id FROM stock
               WHERE LOWER(item_name) = LOWER(?)
                 AND (? = '' OR LOWER(purity) = LOWER(?))
               LIMIT 1
           )""",
        (quantity, item_name, purity, purity),
    )


# ── Public API ────────────────────────────────────────────────

def get_all_invoices() -> list:
    from app.database import get_db
    with get_db() as conn:
        inv_rows  = conn.execute(
            "SELECT * FROM invoices ORDER BY date DESC, time DESC"
        ).fetchall()
        item_rows = conn.execute(
            "SELECT * FROM invoice_items ORDER BY invoice_id, id"
        ).fetchall()

    items_by_inv: dict = {}
    for r in item_rows:
        items_by_inv.setdefault(r["invoice_id"], []).append(dict(r))

    return [
        {**dict(r), "items": items_by_inv.get(r["invoice_id"], [])}
        for r in inv_rows
    ]


def get_invoice_by_id(invoice_id: str) -> Optional[dict]:
    from app.database import get_db
    with get_db() as conn:
        inv  = conn.execute("SELECT * FROM invoices WHERE invoice_id=?", (invoice_id,)).fetchone()
        if not inv:
            return None
        items = conn.execute(
            "SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (invoice_id,)
        ).fetchall()
    return _inv_row_to_dict(inv, items)


def filter_invoices(
    start_date: str = "", end_date: str = "",
    customer: str = "", inv_num: str = "",
) -> list:
    clauses, params = [], []
    if start_date:
        clauses.append("date >= ?");                  params.append(start_date)
    if end_date:
        clauses.append("date <= ?");                  params.append(end_date)
    if customer:
        clauses.append("LOWER(customer_name) LIKE ?"); params.append(f"%{customer.lower()}%")
    if inv_num:
        clauses.append("LOWER(invoice_number) LIKE ?"); params.append(f"%{inv_num.lower()}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    from app.database import get_db
    with get_db() as conn:
        inv_rows = conn.execute(
            f"SELECT * FROM invoices {where} ORDER BY date DESC, time DESC", params
        ).fetchall()
        if not inv_rows:
            return []
        ids = [r["invoice_id"] for r in inv_rows]
        ph  = ",".join("?" * len(ids))
        item_rows = conn.execute(
            f"SELECT * FROM invoice_items WHERE invoice_id IN ({ph}) ORDER BY invoice_id, id", ids
        ).fetchall()

    items_by_inv: dict = {}
    for r in item_rows:
        items_by_inv.setdefault(r["invoice_id"], []).append(dict(r))

    return [
        {**dict(r), "items": items_by_inv.get(r["invoice_id"], [])}
        for r in inv_rows
    ]


def create_invoice(
    customer_name: str,
    customer_mobile: str,
    customer_address: str,
    items: list,
    tax_percent: float,
    notes: str = "",
    customer_email: str = "",
    extra: dict = None,
    invoice_date: str = "",
) -> dict:
    """
    Build and persist a complete invoice in a single atomic transaction.
    - Invoice header, items, stock OUT entries, stock reduction, and
      counter increment all commit together — or all roll back on failure.
    """
    inv_number, next_num = AppConfig.peek_next_invoice_number()
    now      = datetime.now()
    date_str = (invoice_date.strip()
                if invoice_date and invoice_date.strip()
                else now.strftime("%Y-%m-%d"))

    subtotal    = sum(i.get("total", 0) for i in items)
    tax_amount  = round(subtotal * (tax_percent / 100), 2)
    grand_total = round(subtotal + tax_amount, 2)

    inv = {
        "invoice_id":       unique_id(),
        "invoice_number":   inv_number,
        "date":             date_str,
        "time":             now.strftime("%H:%M:%S"),
        "customer_name":    customer_name,
        "customer_mobile":  customer_mobile,
        "customer_address": customer_address,
        "customer_email":   customer_email,
        "subtotal":         round(subtotal, 2),
        "tax_percent":      tax_percent,
        "tax_amount":       tax_amount,
        "grand_total":      grand_total,
        "notes":            notes,
    }
    if extra:
        inv.update(extra)

    # Customer record — separate transaction, acceptable if invoice later fails
    find_or_create_customer(
        customer_name, customer_mobile, customer_address, customer_email,
        aadhaar=extra.get("customer_aadhaar", "") if extra else "",
        pan=extra.get("customer_pan", "") if extra else "",
    )

    from app.database import get_db
    with get_db() as conn:
        # 1. Insert invoice header
        _insert_header(conn, inv)

        # 2. Insert line items
        _insert_items(conn, inv["invoice_id"], items)

        # 3. Commit invoice counter atomically with the invoice row
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('last_invoice_number', ?)",
            (str(next_num),),
        )

        # 4. Stock ledger OUT entries + reduce stock quantities
        for item in items:
            if not item.get("name"):
                continue
            _insert_stock_out(conn, item, inv_number, date_str, customer_name)
            _reduce_stock(conn, item.get("name", ""), int(item.get("quantity", 1)), item.get("purity", ""))

    # Keep in-memory counter in sync
    AppConfig._settings["last_invoice_number"] = next_num

    inv["items"] = items
    return inv


def update_invoice(invoice_id: str, updated_data: dict) -> bool:
    """
    Replace an existing invoice and re-sync stock entries atomically.
    All operations (update header, swap items, undo old stock, apply new stock)
    run inside a single transaction — either all succeed or all roll back.
    """
    from app.database import get_db
    with get_db() as conn:
        # 1. Fetch existing record
        old_inv = conn.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
        ).fetchone()
        if not old_inv:
            return False
        old_items = conn.execute(
            "SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id", (invoice_id,)
        ).fetchall()
        old_items = [dict(r) for r in old_items]
        inv_number = old_inv["invoice_number"]

        # 2. Remove old stock OUT ledger entries for this invoice
        conn.execute(
            "DELETE FROM stock_entries WHERE source = 'invoice' AND voucher_no = ?",
            (inv_number,),
        )

        # 3. Update invoice header
        header_fields = {c: updated_data.get(c, "") for c in _INV_HEADER_COLS if c != "invoice_id"}
        set_clause    = ", ".join(f"{c} = ?" for c in header_fields)
        conn.execute(
            f"UPDATE invoices SET {set_clause} WHERE invoice_id = ?",
            (*header_fields.values(), invoice_id),
        )

        # 4. Replace line items
        conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        _insert_items(conn, invoice_id, updated_data.get("items", []))

        # 5. Restore stock for OLD items (undo previous deductions)
        for item in old_items:
            if item.get("name"):
                _restore_stock(conn, item["name"], int(item.get("quantity", 1)), item.get("purity", ""))

        # 6. Reduce stock for NEW items
        date_str      = updated_data.get("date", "")
        customer_name = updated_data.get("customer_name", "")
        for item in updated_data.get("items", []):
            if item.get("name"):
                _reduce_stock(conn, item["name"], int(item.get("quantity", 1)), item.get("purity", ""))

        # 7. Insert fresh stock OUT ledger entries
        for item in updated_data.get("items", []):
            if item.get("name"):
                _insert_stock_out(conn, item, inv_number, date_str, customer_name)

    # Update customer record outside the main transaction
    find_or_create_customer(
        customer_name,
        updated_data.get("customer_mobile", ""),
        updated_data.get("customer_address", ""),
        updated_data.get("customer_email", ""),
        aadhaar=updated_data.get("customer_aadhaar", ""),
        pan=updated_data.get("customer_pan", ""),
    )
    return True


def delete_invoice(invoice_id: str) -> bool:
    """
    Delete invoice and all its items (CASCADE).
    Restores stock quantities and removes ledger entries atomically.
    """
    from app.database import get_db
    with get_db() as conn:
        inv = conn.execute(
            "SELECT invoice_number FROM invoices WHERE invoice_id = ?", (invoice_id,)
        ).fetchone()
        if not inv:
            return False
        inv_number = inv["invoice_number"]

        old_items = conn.execute(
            "SELECT name, quantity, purity FROM invoice_items WHERE invoice_id = ?", (invoice_id,)
        ).fetchall()

        # Remove stock OUT ledger entries
        conn.execute(
            "DELETE FROM stock_entries WHERE source = 'invoice' AND voucher_no = ?",
            (inv_number,),
        )

        # Restore stock quantities
        for item in old_items:
            if item["name"]:
                _restore_stock(conn, item["name"], int(item["quantity"] or 1), item["purity"] or "")

        # Delete invoice (CASCADE deletes invoice_items)
        conn.execute("DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,))

    return True
