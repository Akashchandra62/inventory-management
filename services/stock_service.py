# services/stock_service.py
from __future__ import annotations
import json
from typing import Optional
from app.utils import unique_id
from models.stock_model import StockModel

_STOCK_COLS = {
    "item_id", "item_name", "category", "purity",
    "gross_weight", "net_weight", "quantity",
    "purchase_price", "selling_price", "vendor_name", "remarks",
}


def _row_to_dict(row) -> dict:
    """Merge standard columns with deserialized custom_data."""
    d = dict(row)
    raw = d.pop("custom_data", "{}")
    try:
        custom = json.loads(raw or "{}")
    except Exception:
        custom = {}
    d.update(custom)
    return d


def _split_custom(data: dict) -> tuple[dict, dict]:
    """Separate standard stock fields from custom ones."""
    standard = {k: v for k, v in data.items() if k in _STOCK_COLS}
    custom   = {k: v for k, v in data.items() if k not in _STOCK_COLS and k != "custom_data"}
    return standard, custom


def get_all_stock() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM stock ORDER BY item_name").fetchall()
    return [_row_to_dict(r) for r in rows]


def add_item(item: StockModel, extra: dict = None) -> bool:
    item.item_id = unique_id()
    d = item.to_dict()
    custom = extra or {}
    from app.database import get_db
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO stock
                   (item_id, item_name, category, purity, gross_weight, net_weight,
                    quantity, purchase_price, selling_price, vendor_name, remarks, custom_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d["item_id"], d["item_name"], d["category"], d["purity"],
                 d["gross_weight"], d["net_weight"], d["quantity"],
                 d["purchase_price"], d["selling_price"], d["vendor_name"],
                 d["remarks"], json.dumps(custom, ensure_ascii=False)),
            )
        return True
    except Exception:
        return False


def update_item(item_id: str, updated: dict) -> bool:
    standard, custom = _split_custom({k: v for k, v in updated.items() if k != "item_id"})

    from app.database import get_db
    try:
        with get_db() as conn:
            # Merge new custom data into existing
            row = conn.execute("SELECT custom_data FROM stock WHERE item_id=?", (item_id,)).fetchone()
            if row is None:
                return False
            try:    existing_custom = json.loads(row["custom_data"] or "{}")
            except: existing_custom = {}
            existing_custom.update(custom)

            sets   = {**standard, "custom_data": json.dumps(existing_custom, ensure_ascii=False)}
            clause = ", ".join(f"{k} = ?" for k in sets)
            result = conn.execute(
                f"UPDATE stock SET {clause} WHERE item_id = ?",
                (*sets.values(), item_id),
            )
        return result.rowcount > 0
    except Exception:
        return False


def delete_item(item_id: str) -> bool:
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute("DELETE FROM stock WHERE item_id = ?", (item_id,))
    return result.rowcount > 0


def get_item_by_id(item_id: str) -> Optional[dict]:
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT * FROM stock WHERE item_id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def reduce_stock(item_name: str, quantity: int, purity: str = "") -> bool:
    """Decrease quantity of first matching stock item (name + optional purity)."""
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute(
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
    return result.rowcount > 0


def restore_stock(item_name: str, quantity: int, purity: str = "") -> bool:
    """Increase quantity — used when an invoice is edited or deleted."""
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute(
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
    return result.rowcount > 0


def get_low_stock(threshold: float = 2, column: str = "quantity") -> list:
    col_map = {
        "quantity":     "quantity",
        "gross_weight": "gross_weight",
        "net_weight":   "net_weight",
    }
    col = col_map.get(column, "quantity")
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM stock WHERE CAST({col} AS REAL) <= ?", (threshold,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]
