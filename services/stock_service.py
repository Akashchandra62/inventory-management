# services/stock_service.py
from typing import Optional
from app.file_manager import safe_read, safe_write
from app.constants import STOCK_FILE
from app.utils import unique_id
from models.stock_model import StockModel


def get_all_stock() -> list:
    return safe_read(STOCK_FILE) or []


def save_all_stock(data: list) -> bool:
    return safe_write(STOCK_FILE, data)


def add_item(item: StockModel) -> bool:
    stock = get_all_stock()
    item.item_id = unique_id()
    stock.append(item.to_dict())
    return save_all_stock(stock)


def update_item(item_id: str, updated: dict) -> bool:
    stock = get_all_stock()
    for i, s in enumerate(stock):
        if s.get("item_id") == item_id:
            stock[i].update(updated)
            return save_all_stock(stock)
    return False


def delete_item(item_id: str) -> bool:
    stock = get_all_stock()
    new = [s for s in stock if s.get("item_id") != item_id]
    return save_all_stock(new)


def get_item_by_id(item_id: str) -> Optional[dict]:
    for s in get_all_stock():
        if s.get("item_id") == item_id:
            return s
    return None


def reduce_stock(item_name: str, quantity: int) -> bool:
    """Reduce stock quantity after a sale."""
    stock = get_all_stock()
    for s in stock:
        if s.get("item_name", "").lower() == item_name.lower():
            s["quantity"] = max(0, s.get("quantity", 0) - quantity)
    return save_all_stock(stock)


def get_low_stock(threshold: int = 2) -> list:
    return [s for s in get_all_stock() if s.get("quantity", 0) <= threshold]
