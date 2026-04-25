# ============================================================
# app/profile_manager.py
# Multi-shop profile support.
# Profile registry lives at C:\JewelryBillingSystem\profiles.json
# Each profile is an independent DATA_ROOT folder.
# ============================================================

import os
import json

_BASE          = r"C:\JewelryBillingSystem"
_PROFILES_FILE = os.path.join(_BASE, "profiles.json")
DEFAULT_ROOT   = _BASE   # backward-compatible: existing single-shop data lives here


# ── Registry helpers ─────────────────────────────────────────

def load_profiles() -> list:
    if not os.path.exists(_PROFILES_FILE):
        return []
    try:
        with open(_PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_profiles(profiles: list):
    os.makedirs(_BASE, exist_ok=True)
    with open(_PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def ensure_default() -> list:
    """
    If no profiles.json exists yet, create a single default entry that
    points to the original data root — fully backward-compatible.
    Returns the profile list.
    """
    profiles = load_profiles()
    if not profiles:
        profiles = [{"name": "Default Shop", "path": DEFAULT_ROOT}]
        save_profiles(profiles)
    return profiles


def get_display_name(profile: dict) -> str:
    """Show the real shop name if the profile is already set up, else fallback."""
    path      = profile.get("path", "")
    shop_file = os.path.join(path, "data", "shop_details.json")
    if os.path.exists(shop_file):
        try:
            with open(shop_file, "r", encoding="utf-8") as f:
                d = json.load(f)
            name = d.get("shop_name", "").strip()
            if name:
                return name
        except Exception:
            pass
    return profile.get("name", path)


# ── Selector dialog ──────────────────────────────────────────

def show_selector(app_name: str) -> str:
    """
    Show the shop-profile picker.
    Returns the chosen DATA_ROOT path, or '' if the user cancelled.
    """
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QPushButton,
        QInputDialog, QMessageBox
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont

    profiles = ensure_default()

    dlg = QDialog()
    dlg.setWindowTitle(f"{app_name} — Select Shop")
    dlg.setMinimumWidth(500)
    dlg.setMinimumHeight(360)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(22, 22, 22, 22)
    layout.setSpacing(12)

    title = QLabel("Select Shop Profile")
    title.setFont(QFont("Segoe UI", 14, QFont.Bold))
    layout.addWidget(title)

    sub = QLabel("Each shop has its own independent data, invoices and settings.")
    sub.setStyleSheet("color:#666; font-size:11px;")
    layout.addWidget(sub)

    lst = QListWidget()
    lst.setAlternatingRowColors(True)
    lst.setMinimumHeight(180)
    lst.setStyleSheet("font-size:12px;")
    layout.addWidget(lst)

    def _refresh():
        lst.clear()
        for p in profiles:
            display = get_display_name(p)
            path    = p.get("path", "")
            item    = QListWidgetItem(f"  {display}\n  {path}")
            item.setData(Qt.UserRole, path)
            lst.addItem(item)
        if lst.count():
            lst.setCurrentRow(0)

    _refresh()

    btn_row = QHBoxLayout()

    btn_new = QPushButton("+ New Shop")
    btn_new.setStyleSheet(
        "background:#27ae60; color:white; border-radius:4px; padding:7px 14px;")

    btn_remove = QPushButton("Remove")
    btn_remove.setStyleSheet(
        "background:#e74c3c; color:white; border-radius:4px; padding:7px 14px;")

    btn_open = QPushButton("Open Selected  ▶")
    btn_open.setDefault(True)
    btn_open.setStyleSheet(
        "background:#2980b9; color:white; border-radius:4px;"
        " padding:7px 20px; font-weight:bold;")

    btn_row.addWidget(btn_new)
    btn_row.addWidget(btn_remove)
    btn_row.addStretch()
    btn_row.addWidget(btn_open)
    layout.addLayout(btn_row)

    _chosen = [""]

    def _open():
        item = lst.currentItem()
        if not item:
            return
        _chosen[0] = item.data(Qt.UserRole)
        dlg.accept()

    def _new():
        name, ok = QInputDialog.getText(
            dlg, "New Shop", "Enter a name for the new shop:")
        if not ok or not name.strip():
            return
        name = name.strip()
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path = os.path.join(_BASE, safe)
        os.makedirs(os.path.join(path, "data"), exist_ok=True)
        profiles.append({"name": name, "path": path})
        save_profiles(profiles)
        _refresh()
        lst.setCurrentRow(lst.count() - 1)

    def _remove():
        item = lst.currentItem()
        if not item:
            return
        if len(profiles) <= 1:
            QMessageBox.warning(dlg, "Cannot Remove",
                                "At least one shop profile must remain.")
            return
        path = item.data(Qt.UserRole)
        ans  = QMessageBox.question(
            dlg, "Remove Profile",
            f"Remove this shop from the list?\n\n{path}\n\n"
            "(Data files on disk are NOT deleted.)",
            QMessageBox.Yes | QMessageBox.No
        )
        if ans == QMessageBox.Yes:
            profiles[:] = [p for p in profiles if p.get("path") != path]
            save_profiles(profiles)
            _refresh()

    btn_open.clicked.connect(_open)
    btn_new.clicked.connect(_new)
    btn_remove.clicked.connect(_remove)
    lst.doubleClicked.connect(_open)

    dlg.exec()
    return _chosen[0]
