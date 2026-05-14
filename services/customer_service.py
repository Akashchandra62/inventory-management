# services/customer_service.py
from app.utils import unique_id


def get_all_customers() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY customer_name").fetchall()
    return [dict(r) for r in rows]


def find_or_create_customer(
    name: str, mobile: str,
    address: str = "", email: str = "",
    aadhaar: str = "", pan: str = "",
) -> str:
    """Return customer_id; phone number is the unique key.
    If a customer with this mobile already exists, update all provided fields.
    If no mobile is given, always create a new record (walk-in customer).
    """
    from app.database import get_db
    with get_db() as conn:
        if mobile:
            row = conn.execute(
                "SELECT customer_id FROM customers WHERE mobile = ?",
                (mobile,),
            ).fetchone()
            if row:
                # Phone matched — update every field that was supplied
                updates = {}
                if name:    updates["customer_name"] = name
                if address: updates["address"]       = address
                if email:   updates["email"]         = email
                if aadhaar: updates["aadhaar"]       = aadhaar
                if pan:     updates["pan"]           = pan
                if updates:
                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    conn.execute(
                        f"UPDATE customers SET {set_clause} WHERE mobile = ?",
                        (*updates.values(), mobile),
                    )
                return row["customer_id"]

        if not mobile:
            return ""  # no phone number — don't create a customer record

        # Mobile not found — create new record
        cid = unique_id()
        conn.execute(
            "INSERT INTO customers "
            "(customer_id, customer_name, mobile, address, email, aadhaar, pan) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, name, mobile, address, email, aadhaar, pan),
        )
        return cid


def update_customer(customer_id: str, updated: dict) -> bool:
    from app.database import get_db
    fields = {k: v for k, v in updated.items() if k != "customer_id"}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    try:
        with get_db() as conn:
            result = conn.execute(
                f"UPDATE customers SET {set_clause} WHERE customer_id = ?",
                (*fields.values(), customer_id),
            )
        return result.rowcount > 0
    except Exception:
        return False


def delete_customer(customer_id: str) -> bool:
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM customers WHERE customer_id = ?", (customer_id,)
        )
    return result.rowcount > 0


def mark_invoice_paid(invoice_id: str, amount: float = 0.0, payment_field: str = "cash_paid") -> bool:
    """Zero the due and add the collected amount to the chosen payment field."""
    from app.database import get_db
    _valid_fields = {"cash_paid", "upi_paid", "card_paid", "cheque_paid"}
    if payment_field not in _valid_fields:
        payment_field = "cash_paid"
    try:
        with get_db() as conn:
            row = conn.execute(
                f"SELECT {payment_field} FROM invoices WHERE invoice_id = ?",
                (invoice_id,),
            ).fetchone()
            if not row:
                return False
            existing = float(row[0] or 0)
            new_val  = round(existing + amount, 2)
            result = conn.execute(
                f"UPDATE invoices SET due_amount = 0, due_date = '', "
                f"{payment_field} = ? WHERE invoice_id = ?",
                (new_val, invoice_id),
            )
        return result.rowcount > 0
    except Exception:
        return False


def search_customers(query: str) -> list:
    from app.database import get_db
    q = f"%{query.lower()}%"
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM customers WHERE LOWER(customer_name) LIKE ? OR mobile LIKE ?",
            (q, q),
        ).fetchall()
    return [dict(r) for r in rows]
