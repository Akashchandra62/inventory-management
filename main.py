#!/usr/bin/env python3
# ============================================================
# main.py - Jewelry Billing System Entry Point
# ============================================================

import sys
import os

# ── Ensure project root is on sys.path ──────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Windows DLL Fix ─────────────────────────────────────────
# MUST run BEFORE any PyQt6 import.
# Fixes: "DLL load failed while importing QtCore"
if sys.platform == "win32":
    try:
        import importlib.util
        spec = importlib.util.find_spec("PyQt5")
        if spec and spec.submodule_search_locations:
            pyqt5_root = list(spec.submodule_search_locations)[0]
            for sub in ["Qt5\\bin", "Qt5\\plugins\\platforms", "Qt5\\plugins"]:
                candidate = os.path.join(pyqt5_root, sub)
                if os.path.isdir(candidate):
                    os.add_dll_directory(candidate)
        python_dir = os.path.dirname(sys.executable)
        if os.path.isdir(python_dir):
            os.add_dll_directory(python_dir)
    except Exception:
        pass

# ── Safe to import PyQt6 now ─────────────────────────────────
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Globally transform all QPushButtons to have the pointing hand cursor on hover
_orig_btn_init = QPushButton.__init__
def _patched_btn_init(self, *args, **kwargs):
    _orig_btn_init(self, *args, **kwargs)
    self.setCursor(Qt.PointingHandCursor)
QPushButton.__init__ = _patched_btn_init

from app.constants import APP_NAME


def setup_logging():
    try:
        from app.constants import LOGS_DIR
        from app.file_manager import ensure_all_folders
        ensure_all_folders()
        log_file = os.path.join(LOGS_DIR, "app.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ]
        )
    except Exception:
        logging.basicConfig(level=logging.INFO)


_FOCUS_QSS = """
QLineEdit:focus {
    border: 2px solid #3498db;
    background-color: #eaf6fd;
    border-radius: 4px;
}
QDoubleSpinBox:focus {
    border: 2px solid #3498db;
    background-color: #eaf6fd;
}
QSpinBox:focus {
    border: 2px solid #3498db;
    background-color: #eaf6fd;
}
QComboBox:focus {
    border: 2px solid #3498db;
    background-color: #eaf6fd;
}
QTextEdit:focus {
    border: 2px solid #3498db;
}
"""


def load_stylesheet(app):
    qss_path = os.path.join(ROOT, "assets", "styles", "main.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    # Always append focus highlights (works for any widget without a custom inline style)
    app.setStyleSheet(app.styleSheet() + _FOCUS_QSS)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))

    # ── Profile Selection ─────────────────────────────────────
    # Must happen BEFORE any data-path-dependent module is imported.
    from app.profile_manager import ensure_default, show_selector
    import app.constants as _c

    profiles = ensure_default()
    if len(profiles) > 1:
        chosen = show_selector(APP_NAME)
        if not chosen:
            sys.exit(0)
        _c.set_data_root(chosen)
    else:
        _c.set_data_root(profiles[0]["path"])

    # ── Now safe to import data-dependent modules ─────────────
    from app.file_manager import initialize_app_storage, is_first_run
    from app.machine_auth import is_authorized
    from app.config import AppConfig
    from app.constants import DATA_ROOT

    # Machine Authorization
    authorized, fingerprint = is_authorized()
    if not authorized:
        QMessageBox.critical(
            None, "Unauthorized Computer",
            f"This software is not authorized for this computer.\n\n"
            f"Machine ID: {fingerprint}\n\nContact your vendor."
        )
        sys.exit(1)

    # Initialize Storage
    try:
        initialize_app_storage()
    except PermissionError:
        QMessageBox.critical(
            None, "Permission Error",
            f"Cannot create data folder:\n{DATA_ROOT}\n\nRun as Administrator once."
        )
        sys.exit(1)
    except Exception as e:
        QMessageBox.critical(None, "Storage Error", f"Init failed:\n{e}")
        sys.exit(1)

    AppConfig.load()
    setup_logging()
    logging.info(f"{APP_NAME} starting. Profile: {DATA_ROOT}  Machine: {fingerprint}")
    load_stylesheet(app)

    # First-Run Setup
    if is_first_run():
        from ui.setup_window import SetupWindow
        setup = SetupWindow()
        if setup.exec() != SetupWindow.DialogCode.Accepted:
            sys.exit(0)
        AppConfig.load()

    # Login + Dashboard
    from ui.login_window import LoginWindow
    from ui.dashboard_window import DashboardWindow

    login     = LoginWindow()
    dashboard = DashboardWindow()

    def on_login_success():
        login.hide()
        dashboard.showMaximized()
        dashboard.refresh_shop_label()

    def on_logout():
        dashboard.hide()
        login.reset()
        login.show()

    login.login_success.connect(on_login_success)
    dashboard.logout_requested.connect(on_logout)
    login.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
