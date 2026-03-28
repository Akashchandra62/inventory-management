# app/config.py - Runtime configuration
from typing import Tuple
from app.file_manager import safe_read, safe_write
from app.constants import SHOP_FILE, SETTINGS_FILE


class AppConfig:
    """Singleton-style config accessor."""

    _shop = {}
    _settings = {}

    @classmethod
    def load(cls):
        cls._shop = safe_read(SHOP_FILE) or {}
        cls._settings = safe_read(SETTINGS_FILE) or {}

    @classmethod
    def shop(cls) -> dict:
        return cls._shop

    @classmethod
    def settings(cls) -> dict:
        return cls._settings

    @classmethod
    def save_shop(cls, data: dict) -> bool:
        cls._shop = data
        return safe_write(SHOP_FILE, data)

    @classmethod
    def save_settings(cls, data: dict) -> bool:
        cls._settings = data
        return safe_write(SETTINGS_FILE, data)

    @classmethod
    def categories(cls) -> list[str]:
        cat_str = cls._shop.get("categories", "Gold, Silver, Diamond, Platinum, Gemstone, Other")
        cats = [c.strip() for c in cat_str.split(",") if c.strip()]
        return cats if cats else ["Gold", "Silver", "Diamond", "Platinum", "Gemstone", "Other"]

    @classmethod
    def invoice_prefix(cls) -> str:
        return cls._shop.get("invoice_prefix", "JB")

    @classmethod
    def default_tax(cls) -> float:
        try:
            return float(cls._shop.get("default_tax", 3.0))
        except (ValueError, TypeError):
            return 3.0

    @classmethod
    def last_invoice_number(cls) -> int:
        try:
            return int(cls._settings.get("last_invoice_number", 0))
        except (ValueError, TypeError):
            return 0

    @classmethod
    def increment_invoice_number(cls) -> Tuple[str, int]:
        last = cls.last_invoice_number()
        next_num = last + 1
        cls._settings["last_invoice_number"] = next_num
        cls.save_settings(cls._settings)
        inv_no = f"{cls.invoice_prefix()}-{next_num:04d}"
        return inv_no, next_num
