# services/metal_service.py
from __future__ import annotations
import uuid
from typing import Optional


def get_metals() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM metals ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def add_metal(name: str, purity: str, rate: float, labour: float) -> bool:
    from app.database import get_db
    name_s   = name.strip()
    purity_s = purity.strip()
    try:
        with get_db() as conn:
            dup = conn.execute(
                "SELECT 1 FROM metals WHERE LOWER(name)=LOWER(?) AND LOWER(purity)=LOWER(?)",
                (name_s, purity_s),
            ).fetchone()
            if dup:
                return False
            conn.execute(
                "INSERT INTO metals (metal_id, name, purity, rate, labour) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4())[:8], name_s, purity_s,
                 round(float(rate), 2), round(float(labour), 2)),
            )
        return True
    except Exception:
        return False


def update_metal(metal_id: str, name: str, purity: str, rate: float, labour: float) -> bool:
    from app.database import get_db
    name_s   = name.strip()
    purity_s = purity.strip()
    try:
        with get_db() as conn:
            dup = conn.execute(
                "SELECT 1 FROM metals WHERE LOWER(name)=LOWER(?) AND LOWER(purity)=LOWER(?)"
                " AND metal_id != ?",
                (name_s, purity_s, metal_id),
            ).fetchone()
            if dup:
                return False
            result = conn.execute(
                "UPDATE metals SET name=?, purity=?, rate=?, labour=? WHERE metal_id=?",
                (name_s, purity_s, round(float(rate), 2),
                 round(float(labour), 2), metal_id),
            )
        return result.rowcount > 0
    except Exception:
        return False


def delete_metal(metal_id: str) -> bool:
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute("DELETE FROM metals WHERE metal_id = ?", (metal_id,))
    return result.rowcount > 0


def get_metal_by_id(metal_id: str) -> Optional[dict]:
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT * FROM metals WHERE metal_id = ?", (metal_id,)).fetchone()
    return dict(row) if row else None
