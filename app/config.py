# app/config.py - Runtime configuration backed by SQLite
import json
import logging
from typing import Tuple

_INT_SETTINGS  = {"last_invoice_number"}
_JSON_SETTINGS = {"stock_custom_columns"}

# Known columns in shop_details table (anything else goes into extra_json)
_SHOP_COLS = {
    "shop_name", "owner_name", "address", "mobile", "gst_number",
    "email", "invoice_prefix", "default_tax", "printer",
    "categories", "item_groups",
}


class AppConfig:
    """Singleton-style config accessor. Same public interface as before."""

    _shop: dict     = {}
    _settings: dict = {}

    @classmethod
    def load(cls):
        from app.database import get_db
        with get_db() as conn:
            row   = conn.execute("SELECT * FROM shop_details WHERE id = 1").fetchone()
            srows = conn.execute("SELECT key, value FROM settings").fetchall()

        if row:
            cls._shop = dict(row)
            # Merge extra_json fields into _shop so all UI code can access them
            raw_extra = cls._shop.pop("extra_json", "{}")
            try:
                extra = json.loads(raw_extra or "{}")
            except Exception:
                extra = {}
            cls._shop.update(extra)
            cls._shop.pop("id", None)
        else:
            cls._shop = {}

        cls._settings = {}
        for r in srows:
            k, v = r["key"], (r["value"] or "")
            if k in _INT_SETTINGS:
                try:    cls._settings[k] = int(v)
                except: cls._settings[k] = 0
            elif k in _JSON_SETTINGS:
                try:    cls._settings[k] = json.loads(v)
                except: cls._settings[k] = []
            else:
                cls._settings[k] = v

    @classmethod
    def shop(cls) -> dict:
        return cls._shop

    @classmethod
    def settings(cls) -> dict:
        return cls._settings

    @classmethod
    def save_shop(cls, data: dict) -> bool:
        """Save shop details. Standard columns go to dedicated columns; anything
        else is serialised into extra_json so no schema changes are needed."""
        from app.database import get_db
        known = {k: data.get(k, "") for k in _SHOP_COLS}
        extra = {k: v for k, v in data.items() if k not in _SHOP_COLS and k != "id"}
        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO shop_details
                        (id, shop_name, owner_name, address, mobile, gst_number,
                         email, invoice_prefix, default_tax, printer,
                         categories, item_groups, extra_json)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        shop_name      = excluded.shop_name,
                        owner_name     = excluded.owner_name,
                        address        = excluded.address,
                        mobile         = excluded.mobile,
                        gst_number     = excluded.gst_number,
                        email          = excluded.email,
                        invoice_prefix = excluded.invoice_prefix,
                        default_tax    = excluded.default_tax,
                        printer        = excluded.printer,
                        categories     = excluded.categories,
                        item_groups    = excluded.item_groups,
                        extra_json     = excluded.extra_json
                """, (
                    known.get("shop_name",      ""),
                    known.get("owner_name",      ""),
                    known.get("address",         ""),
                    known.get("mobile",          ""),
                    known.get("gst_number",      ""),
                    known.get("email",           ""),
                    known.get("invoice_prefix",  "JB"),
                    known.get("default_tax",     3.0),
                    known.get("printer",         ""),
                    known.get("categories",      "Gold,Silver,Diamond,Platinum,Gemstone,Other"),
                    known.get("item_groups",     ""),
                    json.dumps(extra, ensure_ascii=False),
                ))
            cls._shop = data
            return True
        except Exception as e:
            logging.error(f"save_shop failed: {e}")
            return False

    @classmethod
    def save_settings(cls, data: dict) -> bool:
        from app.database import get_db
        try:
            rows = []
            for k, v in data.items():
                if isinstance(v, (list, dict)):
                    rows.append((k, json.dumps(v, ensure_ascii=False)))
                else:
                    rows.append((k, str(v) if v is not None else ""))
            with get_db() as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", rows
                )
            cls._settings = data
            return True
        except Exception as e:
            logging.error(f"save_settings failed: {e}")
            return False

    # ── Derived accessors (unchanged interface) ──────────────

    @classmethod
    def categories(cls) -> list:
        cat_str = cls._shop.get("categories", "Gold,Silver,Diamond,Platinum,Gemstone,Other")
        cats = [c.strip() for c in cat_str.split(",") if c.strip()]
        return cats if cats else ["Gold", "Silver", "Diamond", "Platinum", "Gemstone", "Other"]

    @classmethod
    def item_groups(cls) -> list:
        grp_str = cls._shop.get("item_groups", "")
        return [g.strip() for g in grp_str.split(",") if g.strip()]

    @classmethod
    def invoice_prefix(cls) -> str:
        return cls._shop.get("invoice_prefix", "JB")

    @classmethod
    def default_tax(cls) -> float:
        try:    return float(cls._shop.get("default_tax", 3.0))
        except: return 3.0

    @classmethod
    def custom_stock_columns(cls) -> list:
        return cls._settings.get("stock_custom_columns", [])

    @classmethod
    def save_custom_stock_columns(cls, columns: list) -> bool:
        cls._settings["stock_custom_columns"] = columns
        return cls.save_settings(cls._settings)

    @classmethod
    def low_stock_threshold(cls) -> int:
        try:    return int(cls._settings.get("low_stock_threshold", 5))
        except: return 5

    @classmethod
    def save_low_stock_threshold(cls, threshold: int) -> bool:
        cls._settings["low_stock_threshold"] = threshold
        return cls.save_settings(cls._settings)

    @classmethod
    def last_invoice_number(cls) -> int:
        try:    return int(cls._settings.get("last_invoice_number", 0))
        except: return 0

    @classmethod
    def peek_next_invoice_number(cls) -> Tuple[str, int]:
        """Return next invoice label WITHOUT persisting — call commit_invoice_number() after save."""
        next_num = cls.last_invoice_number() + 1
        inv_no   = f"{cls.invoice_prefix()}-{next_num:04d}"
        return inv_no, next_num

    @classmethod
    def commit_invoice_number(cls, next_num: int) -> bool:
        """Persist the counter after a successful invoice save."""
        cls._settings["last_invoice_number"] = next_num
        return cls.save_settings(cls._settings)

    @classmethod
    def increment_invoice_number(cls) -> Tuple[str, int]:
        inv_no, next_num = cls.peek_next_invoice_number()
        cls.commit_invoice_number(next_num)
        return inv_no, next_num
