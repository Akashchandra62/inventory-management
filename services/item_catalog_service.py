# ============================================================
# services/item_catalog_service.py - Item Catalog (master list)
# Each item: {name, code, category, purity, group, metal_id, rate, labour}
# ============================================================

from app.file_manager import safe_read, safe_write
from app.constants import ITEMS_CATALOG_FILE


def get_catalog() -> list[dict]:
    data = safe_read(ITEMS_CATALOG_FILE)
    return data if isinstance(data, list) else []


def get_names() -> list[str]:
    """Return sorted list of item names for autocomplete."""
    return sorted(i["name"] for i in get_catalog() if i.get("name"))


def get_codes() -> list[str]:
    """Return list of all non-empty item codes (uppercase)."""
    return [i["code"].upper() for i in get_catalog() if i.get("code")]


def _save(catalog: list[dict]) -> bool:
    return safe_write(ITEMS_CATALOG_FILE, catalog)


def add_catalog_item(
    name: str,
    category: str = "",
    purity: str = "",
    code: str = "",
    group: str = "",
    metal_id: str = "",
    rate: float = 0.0,
    labour: float = 0.0,
) -> bool:
    catalog = get_catalog()
    if any(i["name"].lower() == name.lower() for i in catalog):
        return False   # duplicate name
    # Duplicate code check (if code given)
    code_up = code.strip().upper()
    if code_up and any(i.get("code", "").upper() == code_up for i in catalog):
        return False   # duplicate code
    catalog.append({
        "name":     name.strip(),
        "code":     code_up,
        "category": category,
        "purity":   purity,
        "group":    group,
        "metal_id": metal_id,
        "rate":     round(float(rate),   2),
        "labour":   round(float(labour), 2),
    })
    return _save(catalog)


def update_catalog_item(
    old_name: str,
    name: str,
    category: str = "",
    purity: str = "",
    code: str = "",
    group: str = "",
    metal_id: str = "",
    rate: float = 0.0,
    labour: float = 0.0,
) -> bool:
    catalog = get_catalog()
    code_up = code.strip().upper()
    for item in catalog:
        if item["name"].lower() == old_name.lower():
            item["name"]     = name.strip()
            item["code"]     = code_up
            item["category"] = category
            item["purity"]   = purity
            item["group"]    = group
            item["metal_id"] = metal_id
            item["rate"]     = round(float(rate),   2)
            item["labour"]   = round(float(labour), 2)
            return _save(catalog)
    return False


def delete_catalog_item(name: str) -> bool:
    catalog = get_catalog()
    new_cat = [i for i in catalog if i["name"].lower() != name.lower()]
    if len(new_cat) == len(catalog):
        return False
    return _save(new_cat)


def get_item_by_name(name: str) -> dict | None:
    for i in get_catalog():
        if i["name"].lower() == name.lower():
            return i
    return None


def get_item_by_code(code: str) -> dict | None:
    """Look up a catalog item by its shortcut code (case-insensitive)."""
    code = code.strip().upper()
    if not code:
        return None
    for i in get_catalog():
        if i.get("code", "").strip().upper() == code:
            return i
    return None


def ensure_item_exists(name: str, category: str = "") -> None:
    """Auto-add to catalog if not already present (called from StockDialog)."""
    if name.strip():
        add_catalog_item(name.strip(), category)
