# ============================================================
# ui/dashboard_window.py - Main Application Shell
# ============================================================

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
import os
from PyQt6.QtGui import QFont, QPixmap
from app.constants import APP_NAME, APP_VERSION, LOGO_FILE
from app.config import AppConfig

# ── Import all pages ─────────────────────────────────────────
from ui.invoice_page      import InvoicePage
from ui.sales_report_page import SalesReportPage
from ui.stock_page        import StockPage
from ui.stock_report_page import StockReportPage
from ui.vendor_page       import VendorPage
from ui.vendor_report_page import VendorReportPage
from ui.customer_page     import CustomerPage
from ui.settings_page     import SettingsPage
from ui.backup_page       import BackupPage
from ui.home_page         import HomePage


NAV_ITEMS = [
    ("🏠  Dashboard",      "home"),
    ("🧾  New Invoice",     "invoice"),
    ("📊  Sales Report",    "sales_report"),
    ("📋  Invoice History", "invoice_history"),
    ("📦  Stock",           "stock"),
    ("📈  Stock Report",    "stock_report"),
    ("🏪  Vendors",         "vendors"),
    ("📑  Vendor Report",   "vendor_report"),
    ("👥  Customers",       "customers"),
    ("⚙️  Settings",        "settings"),
    ("💾  Backup",          "backup"),
]


class DashboardWindow(QMainWindow):
    """Main window containing sidebar navigation + stacked pages."""

    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 700)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # Logo area
        logo_area = QFrame()
        logo_area.setStyleSheet("background-color: #1a252f; padding: 0px;")
        la = QVBoxLayout(logo_area)
        la.setContentsMargins(15, 20, 15, 15)
        la.setSpacing(2)
        self._gem = QLabel("💎")
        self._gem.setFont(QFont("Segoe UI", 28))
        self._gem.setStyleSheet("color: #f39c12; background: transparent;")
        self._app_lbl = QLabel(APP_NAME)
        self._app_lbl.setObjectName("logo_label")
        self._app_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._app_lbl.setStyleSheet("color: #f39c12; background: transparent;")
        self._app_lbl.setWordWrap(True)
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setObjectName("version_label")
        ver_lbl.setStyleSheet("color: #7f8c8d; font-size: 10px; background: transparent;")
        la.addWidget(self._gem)
        la.addWidget(self._app_lbl)
        la.addWidget(ver_lbl)
        sl.addWidget(logo_area)

        # Nav buttons
        self._nav_buttons: dict[str, QPushButton] = {}
        for label, key in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("sidebar_btn")
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #ecf0f1;
                    border: none; text-align: left;
                    padding: 11px 20px; font-size: 13px;
                }
                QPushButton:hover { background: #34495e; }
                QPushButton:checked { background: #f39c12; color: white; font-weight: bold; }
            """)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            sl.addWidget(btn)
            self._nav_buttons[key] = btn

        sl.addStretch()

        # Shop info at bottom
        self._shop_lbl = QLabel()
        self._shop_lbl.setWordWrap(True)
        self._shop_lbl.setStyleSheet(
            "color: #95a5a6; font-size: 10px; background: transparent; padding: 5px 12px;"
        )
        sl.addWidget(self._shop_lbl)

        # Logout
        btn_logout = QPushButton("🚪  Logout")
        btn_logout.setStyleSheet("""
            QPushButton {
                background: #c0392b; color: white; border: none;
                padding: 12px 20px; font-size: 13px; text-align: left;
            }
            QPushButton:hover { background: #e74c3c; }
        """)
        btn_logout.clicked.connect(self._logout)
        sl.addWidget(btn_logout)

        layout.addWidget(sidebar)

        # ── Stacked Pages ────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        self._pages: dict[str, QWidget] = {}

        pages = {
            "home":            HomePage(),
            "invoice":         InvoicePage(),
            "sales_report":    SalesReportPage(),
            "invoice_history": SalesReportPage(history_mode=True),
            "stock":           StockPage(),
            "stock_report":    StockReportPage(),
            "vendors":         VendorPage(),
            "vendor_report":   VendorReportPage(),
            "customers":       CustomerPage(),
            "settings":        SettingsPage(),
            "backup":          BackupPage(),
        }

        for key, page in pages.items():
            self._stack.addWidget(page)
            self._pages[key] = page

        layout.addWidget(self._stack)

        self._switch_page("home")

    def _switch_page(self, key: str):
        # Uncheck all nav buttons, check selected
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)

        page = self._pages.get(key)
        if page:
            # Refresh page data when switching
            if hasattr(page, "refresh"):
                page.refresh()
            self._stack.setCurrentWidget(page)

    def _logout(self):
        reply = QMessageBox.question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()

    def refresh_shop_label(self):
        shop = AppConfig.shop()
        shop_name = shop.get('shop_name', '').strip()
        self._shop_lbl.setText(f"{shop_name}\n{shop.get('mobile','')}")
        self._app_lbl.setText(shop_name if shop_name else APP_NAME)
        
        if os.path.exists(LOGO_FILE):
            pix = QPixmap(LOGO_FILE).scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._gem.setPixmap(pix)
            self._gem.setText("")
        else:
            self._gem.setPixmap(QPixmap())
            self._gem.setText("💎")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_shop_label()
