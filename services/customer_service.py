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
    """Return customer_id; create record if not found by mobile."""
    from app.database import get_db
    with get_db() as conn:
        if mobile:
            row = conn.execute(
                "SELECT customer_id, email, aadhaar, pan FROM customers WHERE mobile = ?",
                (mobile,),
            ).fetchone()
            if row:
                updates = {}
                if email   and not row["email"]:   updates["email"]   = email
                if aadhaar and not row["aadhaar"]: updates["aadhaar"] = aadhaar
                if pan     and not row["pan"]:     updates["pan"]     = pan
                if updates:
                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    conn.execute(
                        f"UPDATE customers SET {set_clause} WHERE mobile = ?",
                        (*updates.values(), mobile),
                    )
                return row["customer_id"]

        # Create new customer
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


def search_customers(query: str) -> list:
    from app.database import get_db
    q = f"%{query.lower()}%"
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM customers WHERE LOWER(customer_name) LIKE ? OR mobile LIKE ?",
            (q, q),
        ).fetchall()
    return [dict(r) for r in rows]
