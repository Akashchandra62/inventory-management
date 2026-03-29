# ============================================================
# services/item_catalog_service.py - Item Catalog (master list)
# ============================================================

from app.file_manager import safe_read, safe_write
from app.constants import ITEMS_CATALOG_FILE


def get_catalog() -> list[dict]:
    """Return all catalog items. Each item: {name, category, purity}"""
    data = safe_read(ITEMS_CATALOG_FILE)
    return data if isinstance(data, list) else []


def get_names() -> list[str]:
    """Return sorted list of item names for autocomplete."""
    return sorted(i["name"] for i in get_catalog() if i.get("name"))


def _save(catalog: list[dict]) -> bool:
    return safe_write(ITEMS_CATALOG_FILE, catalog)


def add_catalog_item(name: str, category: str = "", purity: str = "") -> bool:
    catalog = get_catalog()
    if any(i["name"].lower() == name.lower() for i in catalog):
        return False   # duplicate
    catalog.append({"name": name, "category": category, "purity": purity})
    return _save(catalog)


def update_catalog_item(old_name: str, name: str, category: str = "", purity: str = "") -> bool:
    catalog = get_catalog()
    for item in catalog:
        if item["name"].lower() == old_name.lower():
            item["name"]     = name
            item["category"] = category
            item["purity"]   = purity
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


def ensure_item_exists(name: str, category: str = "") -> None:
    """Auto-add to catalog if not already present (called from StockDialog)."""
    if name.strip():
        add_catalog_item(name.strip(), category)
