# Jewelry Billing System — Project Instructions

## Windows 7 / Windows 8 Compatibility — MANDATORY

**The client runs Windows 7 and Windows 8. All code must be compatible with Python 3.8.x.**

Python 3.8 is the last version that supports Windows 7/8. The PyInstaller `.exe` bundles Python 3.8, so the client never installs Python themselves — but we must write code that runs on 3.8.

### Rules to follow every time you write code

- **No `X | Y` union type hints** — `dict | None`, `str | int`, etc. require Python 3.10+. Use `Optional[X]` from `typing` instead.
- **No `list[str]`, `dict[str, X]`, `tuple[X, Y]` in function signatures** without `from __future__ import annotations` at the top of the file. These subscript forms require Python 3.9+. Either add the future import or use `List[str]`, `Dict[str, X]`, `Tuple[X, Y]` from `typing`.
- **No `match` / `case` statements** — Python 3.10+ only.
- **No walrus operator `:=` inside comprehensions in complex ways** — walrus was added in 3.8 so it's fine, but double-check edge cases.
- **`shutil.copytree(dirs_exist_ok=True)`** — added in Python 3.8, OK to use. But prefer explicit `rmtree` + `copytree` for clarity.
- **`os.add_dll_directory()`** — Python 3.8+, already wrapped in try/except in `main.py`. Keep it that way.
- **No f-string `=` debugging syntax** like `f"{x=}"` — Python 3.8+, technically fine, but avoid for clarity.
- **`typing.TypedDict`, `typing.Protocol`** — available from Python 3.8, fine to use.

### Quick fix pattern

If you write a file with subscript annotations, add this at the very top:

```python
from __future__ import annotations
```

This makes all annotations lazy (string-based) and backports `list[str]`, `dict[str, X]`, `X | Y` etc. to Python 3.7+.

---

## Project Overview

Desktop billing app for Indian jewelry shops. Offline-only, single-user, Windows-only.

- **GUI:** PyQt5 ≥ 5.15
- **Storage:** SQLite — single `jewelry.db` per shop profile (`app/database.py`)
- **PDF:** ReportLab
- **Packaging:** PyInstaller → standalone `.exe`

### Data location

```
C:\JewelryBillingSystem\        ← default DATA_ROOT (overridden by set_data_root())
    <ShopName>\
        data\jewelry.db         ← all data
        assets\                 ← logo, QR, certificate images
        backups\
        invoices_print\
        logs\
    profiles.json               ← multi-shop registry
```

### Architecture

```
UI (PyQt5, ui/)  →  Services (services/)  →  SQLite (app/database.py)
```

- `app/database.py` — `get_db()` context manager, schema, `init_db()`
- `app/constants.py` — all paths including `DB_FILE`; `set_data_root()` for profile switching
- `app/config.py` — `AppConfig` singleton; reads `shop_details` + `settings` tables
- `app/file_manager.py` — folder creation + calls `init_db()`
- `app/profile_manager.py` — multi-shop selector; pendrive profiles supported

### Key rules for invoice service

`services/invoice_service.py` — `create_invoice()` and `update_invoice()` run everything (header, items, stock entries, stock reduction, counter increment) in a **single SQLite transaction**. Never split these into separate transactions.

### Pendrive profile support

A shop profile's `path` can point to any drive letter (e.g. `E:\ShopData`). When the pendrive is removed, `is_profile_available()` returns False and the profile is shown as unavailable in the selector. Data never touches the laptop for that profile.
