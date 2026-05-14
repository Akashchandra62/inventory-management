# services/stock_entry_service.py — Stock IN / OUT ledger
from app.utils import unique_id, current_date_str

_ENTRY_COLS = {
    "entry_id", "entry_type", "source", "voucher_no", "voucher_date",
    "metal_type", "item_name", "sub_name", "purity", "dabba_name", "dabba_wt",
    "gross_wt", "plastic_wt", "qty_in", "less_wt", "dia_wt", "net_wt",
    "location", "out_gross_wt", "out_less_wt", "out_net_wt", "qty_out",
    "remarks", "invoice_id", "rate", "amount", "vendor_name", "description",
}


def _to_entry(row) -> dict:
    return dict(row)


def get_all_entries() -> list:
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM stock_entries ORDER BY voucher_date DESC, rowid DESC"
        ).fetchall()
    return [_to_entry(r) for r in rows]


def add_entry(entry: dict) -> bool:
    entry["entry_id"] = unique_id()
    known = {k: entry.get(k, "") for k in _ENTRY_COLS}
    cols  = ", ".join(known.keys())
    placeholders = ", ".join("?" * len(known))
    from app.database import get_db
    try:
        with get_db() as conn:
            conn.execute(
                f"INSERT INTO stock_entries ({cols}) VALUES ({placeholders})",
                list(known.values()),
            )
        return True
    except Exception:
        return False


def delete_entry(entry_id: str) -> bool:
    from app.database import get_db
    with get_db() as conn:
        result = conn.execute(
            "DELETE FROM stock_entries WHERE entry_id = ?", (entry_id,)
        )
    return result.rowcount > 0


def get_next_voucher_no() -> str:
    from app.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(voucher_no, 5) AS INTEGER)) AS max_n"
            " FROM stock_entries WHERE voucher_no LIKE 'VCH-%'"
        ).fetchone()
    max_n = row["max_n"] or 0
    return f"VCH-{max_n + 1:04d}"


def get_inventory() -> list:
    """Aggregate stock_entries into current inventory by (metal_type, item_name, sub_name, purity)."""
    from app.database import get_db
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM stock_entries").fetchall()

    groups: dict = {}
    for e in rows:
        key = (
            e["metal_type"] or "",
            e["item_name"]  or "",
            e["sub_name"]   or "",
            e["purity"]     or "",
        )
        if key not in groups:
            groups[key] = {
                "metal_type": key[0], "item_name": key[1],
                "sub_name":   key[2], "purity":    key[3],
                "wt_in":  0.0, "wt_out": 0.0,
                "qty_in": 0,   "qty_out": 0,
                "_locations": set(), "location": "",
                "last_date": "",
            }
        g  = groups[key]
        et = e["entry_type"] or "IN"
        if et == "IN":
            g["wt_in"]  += e["net_wt"]  or 0.0
            g["qty_in"] += e["qty_in"]  or 0
            if e["location"]:
                g["_locations"].add(e["location"])
        else:
            g["wt_out"]  += e["out_net_wt"] or 0.0
            g["qty_out"] += e["qty_out"]    or 0
        d = e["voucher_date"] or ""
        if d > g["last_date"]:
            g["last_date"] = d

    result = []
    for g in groups.values():
        g["location"]    = ", ".join(sorted(g.pop("_locations")))
        g["current_wt"]  = round(g["wt_in"] - g["wt_out"], 3)
        g["current_qty"] = g["qty_in"] - g["qty_out"]
        result.append(g)
    return result


# kept for backward-compat callers (invoice_service uses this alias)
def save_all_entries(entries: list) -> bool:
    """Replace all stock entries — used only by invoice update rollback path."""
    from app.database import get_db
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM stock_entries")
            for entry in entries:
                known = {k: entry.get(k, "") for k in _ENTRY_COLS}
                cols  = ", ".join(known.keys())
                placeholders = ", ".join("?" * len(known))
                conn.execute(
                    f"INSERT INTO stock_entries ({cols}) VALUES ({placeholders})",
                    list(known.values()),
                )
        return True
    except Exception:
        return False
