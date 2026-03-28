# services/vendor_service.py
from app.file_manager import safe_read, safe_write
from app.constants import VENDORS_FILE
from app.utils import unique_id
from models.vendor_model import VendorModel


def get_all_vendors() -> list:
    return safe_read(VENDORS_FILE) or []


def save_all_vendors(data: list) -> bool:
    return safe_write(VENDORS_FILE, data)


def add_vendor(vendor: VendorModel) -> bool:
    vendors = get_all_vendors()
    vendor.vendor_id = unique_id()
    vendors.append(vendor.to_dict())
    return save_all_vendors(vendors)


def update_vendor(vendor_id: str, updated: dict) -> bool:
    vendors = get_all_vendors()
    for i, v in enumerate(vendors):
        if v.get("vendor_id") == vendor_id:
            vendors[i].update(updated)
            return save_all_vendors(vendors)
    return False


def delete_vendor(vendor_id: str) -> bool:
    vendors = get_all_vendors()
    new = [v for v in vendors if v.get("vendor_id") != vendor_id]
    return save_all_vendors(new)
