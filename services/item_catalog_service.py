# services/item_catalog_service.py
from __future__ import annotations
import uuid
from typing import Optional


def get_catalog() -> list[dict]:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ic.*, m.name AS metal_name
            FROM item_catalog ic
            LEFT JOIN metals m ON ic.metal_id = m.metal_id
            ORDER BY ic.name
        """).fetchall()
    return [dict(r) for r in rows]


def get_names() -> list[str]:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT name FROM item_catalog ORDER BY name").fetchall()
    return [r["name"] for r in rows]


def get_codes() -> list[str]:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT code FROM item_catalog WHERE code != '' ORDER BY code"
        ).fetchall()
    return [r["code"].upper() for r in rows]


def add_catalog_item(
    name: str, category: str = "", purity: str = "", code: str = "",
    group: str = "", metal_id: str = "", rate: float = 0.0, labour: float = 0.0,
) -> bool:
    from app.database import get_db
    code_up = code.strip().upper()
    try:
        with get_db() as conn:
            # Duplicate (name + purity) check — same name with different purity is allowed
            dup_name = conn.execute(
                "SELECT 1 FROM item_catalog"
                " WHERE LOWER(name) = LOWER(?) AND LOWER(purity) = LOWER(?)",
                (name, purity.strip()),
            ).fetchone()
            if dup_name:
                return False
            # Duplicate code check (only if code provided)
            if code_up:
                dup_code = conn.execute(
                    "SELECT 1 FROM item_catalog WHERE UPPER(code) = ?", (code_up,)
                ).fetchone()
                if dup_code:
                    return False
            conn.execute(
                "INSERT INTO item_catalog"
                " (catalog_id, name, code, category, purity, item_group, metal_id, rate, labour)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4())[:8], name.strip(), code_up, category,
                 purity, group, metal_id, round(float(rate), 2), round(float(labour), 2)),
            )
        return True
    except Exception:
        return False


def update_catalog_item(
    old_name: str, name: str, category: str = "", purity: str = "", code: str = "",
    group: str = "", metal_id: str = "", rate: float = 0.0, labour: float = 0.0,
) -> bool:
    from app.database import get_db
    code_up = code.strip().upper()
    try:
        with get_db() as conn:
            result = conn.execute(
                """UPDATE item_catalog SET
                    name=?, code=?, category=?, purity=?, item_group=?, metal_id=?, rate=?, labour=?
                   WHERE LOWER(name) = LOWER(?)""",
                (name.strip(), code_up, category, purity, group, metal_id,
                 round(float(rate), 2), round(float(labour), 2), old_name),
            )
        return result.rowcount > 0
    except Exception:
        return False


def delete_catalog_item(name: str) -> bool:
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM item_catalog WHERE LOWER(name) = LOWER(?)", (name,)
        )
    return result.rowcount > 0


def get_item_by_name(name: str) -> Optional[dict]:
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM item_catalog WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
    return dict(row) if row else None


def get_item_by_code(code: str) -> Optional[dict]:
    code = code.strip().upper()
    if not code:
        return None
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM item_catalog WHERE UPPER(code) = ?", (code,)
        ).fetchone()
    return dict(row) if row else None


def ensure_item_exists(name: str, category: str = "") -> None:
    if name.strip():
        add_catalog_item(name.strip(), category)
