# ============================================================
# app/profile_manager.py
# Multi-shop profile support.
# Profile registry lives at C:\JewelryBillingSystem\profiles.json
# Each profile is an independent DATA_ROOT folder.
# Supports laptop profiles AND external-drive (pendrive) profiles.
# ============================================================

import os
import json

_BASE          = r"C:\JewelryBillingSystem"
_PROFILES_FILE = os.path.join(_BASE, "profiles.json")
DEFAULT_ROOT   = _BASE


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
    profiles = load_profiles()
    if not profiles:
        profiles = [{"name": "Default Shop", "path": DEFAULT_ROOT}]
        save_profiles(profiles)
    return profiles


def is_profile_available(profile: dict) -> bool:
    """Return True if the profile's data directory is accessible (drive mounted)."""
    path = profile.get("path", "")
    return bool(path) and os.path.exists(path)


def get_display_name(profile: dict) -> str:
    """Return the real shop name from the SQLite DB, falling back to the profile name."""
    path    = profile.get("path", "")
    db_path = os.path.join(path, "data", "jewelry.db")
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT shop_name FROM shop_details WHERE id = 1"
            ).fetchone()
            conn.close()
            if row:
                name = (row["shop_name"] or "").strip()
                if name:
                    return name
        except Exception:
            pass
    return profile.get("name", path)


# ── Selector dialog ──────────────────────────────────────────

def show_selector(app_name: str) -> str:
    """
    Show the shop-profile picker.
    Profiles stored on unavailable drives (pendrive not inserted) are
    shown but disabled with an 'Unavailable' badge.
    Returns the chosen DATA_ROOT path, or '' if the user cancelled.
    """
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QPushButton,
        QInputDialog, QMessageBox, QFileDialog,
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont, QColor

    profiles = ensure_default()

    dlg = QDialog()
    dlg.setWindowTitle(f"{app_name} — Select Shop")
    dlg.setMinimumWidth(540)
    dlg.setMinimumHeight(380)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(22, 22, 22, 22)
    layout.setSpacing(12)

    title = QLabel("Select Shop Profile")
    title.setFont(QFont("Segoe UI", 14, QFont.Bold))
    layout.addWidget(title)

    sub = QLabel("Pendrive profiles appear as Unavailable when the drive is not connected.")
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
            available = is_profile_available(p)
            display   = get_display_name(p)
            path      = p.get("path", "")
            badge     = "✓ Available" if available else "✗ Unavailable (drive not found)"
            item      = QListWidgetItem(f"  {display}\n  {path}   [{badge}]")
            item.setData(Qt.UserRole, path)
            item.setData(Qt.UserRole + 1, available)
            if not available:
                item.setForeground(QColor("#aaa"))
            lst.addItem(item)
        if lst.count():
            lst.setCurrentRow(0)

    _refresh()

    btn_row = QHBoxLayout()

    btn_new_local = QPushButton("+ New Shop (Laptop)")
    btn_new_local.setStyleSheet(
        "background:#27ae60; color:white; border-radius:4px; padding:7px 14px;")

    btn_new_drive = QPushButton("+ New Shop (Pendrive)")
    btn_new_drive.setStyleSheet(
        "background:#8e44ad; color:white; border-radius:4px; padding:7px 14px;")

    btn_remove = QPushButton("Remove")
    btn_remove.setStyleSheet(
        "background:#e74c3c; color:white; border-radius:4px; padding:7px 14px;")

    btn_open = QPushButton("Open Selected  ▶")
    btn_open.setDefault(True)
    btn_open.setStyleSheet(
        "background:#2980b9; color:white; border-radius:4px;"
        " padding:7px 20px; font-weight:bold;")

    btn_row.addWidget(btn_new_local)
    btn_row.addWidget(btn_new_drive)
    btn_row.addWidget(btn_remove)
    btn_row.addStretch()
    btn_row.addWidget(btn_open)
    layout.addLayout(btn_row)

    _chosen = [""]

    def _open():
        item = lst.currentItem()
        if not item:
            return
        available = item.data(Qt.UserRole + 1)
        if not available:
            QMessageBox.warning(
                dlg, "Drive Unavailable",
                "This profile's drive is not connected.\n\n"
                "Please insert the pendrive and try again."
            )
            return
        _chosen[0] = item.data(Qt.UserRole)
        dlg.accept()

    def _new_local():
        name, ok = QInputDialog.getText(dlg, "New Shop", "Enter a name for the new shop:")
        if not ok or not name.strip():
            return
        name  = name.strip()
        safe  = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path  = os.path.join(_BASE, safe)
        os.makedirs(os.path.join(path, "data"), exist_ok=True)
        profiles.append({"name": name, "path": path})
        save_profiles(profiles)
        _refresh()
        lst.setCurrentRow(lst.count() - 1)

    def _new_drive():
        folder = QFileDialog.getExistingDirectory(
            dlg, "Select folder on pendrive for shop data",
            "", QFileDialog.ShowDirsOnly,
        )
        if not folder:
            return
        name, ok = QInputDialog.getText(dlg, "New Shop", "Enter a name for this pendrive shop:")
        if not ok or not name.strip():
            return
        name = name.strip()
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        path = os.path.join(folder, safe)
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
            QMessageBox.Yes | QMessageBox.No,
        )
        if ans == QMessageBox.Yes:
            profiles[:] = [p for p in profiles if p.get("path") != path]
            save_profiles(profiles)
            _refresh()

    btn_open.clicked.connect(_open)
    btn_new_local.clicked.connect(_new_local)
    btn_new_drive.clicked.connect(_new_drive)
    btn_remove.clicked.connect(_remove)
    lst.doubleClicked.connect(_open)

    dlg.exec()
    return _chosen[0]
