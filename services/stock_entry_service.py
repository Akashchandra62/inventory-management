# ============================================================
# services/stock_entry_service.py — Stock IN / OUT ledger
# ============================================================

import app.constants as _c
from app.file_manager import safe_read, safe_write
from app.utils import unique_id, current_date_str


def _path() -> str:
    return _c.STOCK_ENTRY_FILE


def get_all_entries() -> list:
    data = safe_read(_path())
    return data if isinstance(data, list) else []


def save_all_entries(data: list) -> bool:
    return safe_write(_path(), data)


def add_entry(entry: dict) -> bool:
    entries = get_all_entries()
    entry["entry_id"] = unique_id()
    entries.append(entry)
    return save_all_entries(entries)


def delete_entry(entry_id: str) -> bool:
    entries = get_all_entries()
    new = [e for e in entries if e.get("entry_id") != entry_id]
    if len(new) == len(entries):
        return False
    return save_all_entries(new)


def get_next_voucher_no() -> str:
    """Return next auto-incremented voucher number (VCH-0001 format)."""
    entries = get_all_entries()
    max_n = 0
    for e in entries:
        v = e.get("voucher_no", "")
        if v.upper().startswith("VCH-"):
            try:
                max_n = max(max_n, int(v[4:]))
            except ValueError:
                pass
    return f"VCH-{max_n + 1:04d}"


def get_inventory() -> list:
    """Aggregate all entries into current inventory grouped by (metal, item, sub_name, purity)."""
    entries = get_all_entries()
    groups: dict = {}
    for e in entries:
        key = (
            e.get("metal_type", ""),
            e.get("item_name",  ""),
            e.get("sub_name",   ""),
            e.get("purity",     ""),
        )
        if key not in groups:
            groups[key] = {
                "metal_type": key[0],
                "item_name":  key[1],
                "sub_name":   key[2],
                "purity":     key[3],
                "wt_in":      0.0,
                "wt_out":     0.0,
                "qty_in":     0,
                "qty_out":    0,
                "location":   "",
                "last_date":  "",
            }
        g = groups[key]
        et = e.get("entry_type", "IN")
        if et == "IN":
            g["wt_in"]  += e.get("net_wt",  0.0)
            g["qty_in"] += e.get("qty_in",   0)
            if e.get("location"):
                g["location"] = e.get("location")
        else:
            g["wt_out"]  += e.get("out_net_wt", 0.0)
            g["qty_out"] += e.get("qty_out",     0)
        d = e.get("voucher_date", "")
        if d > g["last_date"]:
            g["last_date"] = d

    result = []
    for g in groups.values():
        g["current_wt"]  = round(g["wt_in"] - g["wt_out"], 3)
        g["current_qty"] = g["qty_in"] - g["qty_out"]
        result.append(g)
    return result
