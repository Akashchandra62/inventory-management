# services/vendor_service.py
from app.utils import unique_id
from models.vendor_model import VendorModel


def get_all_vendors() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM vendors ORDER BY vendor_name").fetchall()
    return [dict(r) for r in rows]


def add_vendor(vendor: VendorModel) -> bool:
    vendor.vendor_id = unique_id()
    d = vendor.to_dict()
    from app.database import get_db
    try:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT 1 FROM vendors WHERE LOWER(vendor_name) = LOWER(?)",
                (d["vendor_name"],),
            ).fetchone()
            if existing:
                return False
            conn.execute(
                "INSERT INTO vendors (vendor_id, vendor_name, phone, address, gst_number, email, notes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (d["vendor_id"], d["vendor_name"], d.get("phone", ""),
                 d.get("address", ""), d.get("gst_number", ""),
                 d.get("email", ""), d.get("notes", "")),
            )
        return True
    except Exception:
        return False


def update_vendor(vendor_id: str, updated: dict) -> bool:
    fields = {k: v for k, v in updated.items() if k != "vendor_id"}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    from app.database import get_db
    try:
        with get_db() as conn:
            result = conn.execute(
                f"UPDATE vendors SET {set_clause} WHERE vendor_id = ?",
                (*fields.values(), vendor_id),
            )
        return result.rowcount > 0
    except Exception:
        return False


def delete_vendor(vendor_id: str) -> bool:
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute("DELETE FROM vendors WHERE vendor_id = ?", (vendor_id,))
    return result.rowcount > 0
