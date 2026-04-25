# ============================================================
# services/metal_service.py - Metals / Rate-card master list
# Each record: {id, name, purity, rate, labour}
# ============================================================

import uuid
from app.file_manager import safe_read, safe_write
from app.constants import METALS_FILE


def get_metals() -> list[dict]:
    data = safe_read(METALS_FILE)
    return data if isinstance(data, list) else []


def _save(metals: list[dict]) -> bool:
    return safe_write(METALS_FILE, metals)


def add_metal(name: str, purity: str, rate: float, labour: float) -> bool:
    metals = get_metals()
    metals.append({
        "id":     str(uuid.uuid4())[:8],
        "name":   name.strip(),
        "purity": purity.strip(),
        "rate":   round(float(rate),   2),
        "labour": round(float(labour), 2),
    })
    return _save(metals)


def update_metal(metal_id: str, name: str, purity: str, rate: float, labour: float) -> bool:
    metals = get_metals()
    for m in metals:
        if m.get("id") == metal_id:
            m["name"]   = name.strip()
            m["purity"] = purity.strip()
            m["rate"]   = round(float(rate),   2)
            m["labour"] = round(float(labour), 2)
            return _save(metals)
    return False


def delete_metal(metal_id: str) -> bool:
    metals  = get_metals()
    new_lst = [m for m in metals if m.get("id") != metal_id]
    if len(new_lst) == len(metals):
        return False
    return _save(new_lst)


def get_metal_by_id(metal_id: str) -> dict | None:
    for m in get_metals():
        if m.get("id") == metal_id:
            return m
    return None
