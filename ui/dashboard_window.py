# ============================================================
# ui/dashboard_window.py - Main Application Shell
# ============================================================

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QPoint
import os
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon, QPolygon
from app.constants import APP_NAME, APP_VERSION, LOGO_FILE
from app.config import AppConfig

from ui.invoice_page       import InvoicePage
from ui.sales_report_page  import SalesReportPage, ItemSalesReportPage, DatewiseSalesPage
from ui.stock_page         import StockPage
from ui.stock_report_page  import ItemwiseStockPage, MetalwiseStockPage, DatewiseStockPage
from ui.stock_entry_page   import StockEntryPage
from ui.customer_page      import CustomerPage
from ui.settings_page      import SettingsPage
from ui.backup_page        import BackupPage
from ui.home_page          import HomePage
from ui.karigar_page       import KarigarPage, KarigarDirectoryPage


# (label, page-key, badge-letter, badge-color)
NAV_ITEMS = [
    ("  Dashboard",       "home",            "D", "#f39c12"),
    ("  New Invoice",     "invoice",         "I", "#27ae60"),
    ("  Invoice History", "invoice_history", "H", "#8e44ad"),
    ("  Stock",           "stock",           "S", "#16a085"),
    ("  Stock Entry",     "stock_entry",     "E", "#0e6655"),
    ("  Vendor",           "karigar",           "K", "#8e44ad"),
    ("  Vendor Directory","karigar_directory", "K", "#6c3483"),
    ("  Customers",        "customers",         "C", "#1abc9c"),
    ("  Settings",        "settings",        "G", "#555e6d"),
    ("  Backup",          "backup",          "B", "#e74c3c"),
]


def _nav_icon(letter: str, bg: str) -> QIcon:
    """Colored rounded-rect icon with a white letter drawn by QPainter.
    No emoji / glyph required — works on any Windows install."""
    size = 24
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(bg))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(1, 1, size - 2, size - 2, 5, 5)
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI", 9, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, letter)
    p.end()
    return QIcon(pix)


def _arrow_icon(direction: str, canvas: int = 32) -> QIcon:
    """QPainter-drawn triangle arrow on a canvas that fills the whole button."""
    pix = QPixmap(canvas, canvas)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#ecf0f1"))
    p.setPen(Qt.NoPen)
    m  = canvas // 4        # margin from edge
    cx = canvas // 2        # center x
    cy = canvas // 2        # center y
    arm = canvas // 4       # half-height of triangle
    if direction == "left":
        pts = QPolygon([QPoint(cx + m, cy - arm),
                        QPoint(cx - m, cy),
                        QPoint(cx + m, cy + arm)])
    else:
        pts = QPolygon([QPoint(cx - m, cy - arm),
                        QPoint(cx + m, cy),
                        QPoint(cx - m, cy + arm)])
    p.drawPolygon(pts)
    p.end()
    return QIcon(pix)


def _gem_pixmap(size: int = 44) -> QPixmap:
    """Amber diamond shape for when no shop logo has been uploaded."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    half = size // 2
    diamond = QPolygon([
        QPoint(half,      2),
        QPoint(size - 3,  half),
        QPoint(half,      size - 2),
        QPoint(3,         half),
    ])
    p.setBrush(QColor("#f39c12"))
    p.setPen(Qt.NoPen)
    p.drawPolygon(diamond)
    p.end()
    return pix

SIDEBAR_EXPANDED  = 220
SIDEBAR_COLLAPSED = 44      # visible rail, not zero


class DashboardWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 700)
        self._sidebar_expanded = True
        self._build_ui()

    # ─────────────────────────────────────────────────────────
    #  Build UI
    # ─────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ══ SIDEBAR ══════════════════════════════════════════
        self._sidebar = QFrame()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setStyleSheet("background-color: #2c3e50;")
        self._sidebar.setMinimumWidth(SIDEBAR_COLLAPSED)
        self._sidebar.setMaximumWidth(SIDEBAR_EXPANDED)
        sl = QVBoxLayout(self._sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # ── Toggle strip (always visible) ─────────────────────
        toggle_strip = QFrame()
        toggle_strip.setFixedHeight(44)
        toggle_strip.setStyleSheet("background-color: #1a252f;")
        ts = QHBoxLayout(toggle_strip)
        ts.setContentsMargins(0, 0, 0, 0)
        ts.setSpacing(0)

        ts.addStretch(1)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setIcon(_arrow_icon("left"))
        self._toggle_btn.setIconSize(QSize(32, 32))
        self._toggle_btn.setFixedSize(32, 32)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setToolTip("Collapse sidebar")
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a252f;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_sidebar)
        ts.addWidget(self._toggle_btn)
        ts.addSpacing(6)

        sl.addWidget(toggle_strip)

        # ── Logo block ────────────────────────────────────────
        self._logo_area = QFrame()
        self._logo_area.setStyleSheet("background-color: #1a252f;")
        la = QVBoxLayout(self._logo_area)
        la.setContentsMargins(15, 10, 15, 14)
        la.setSpacing(3)

        self._gem = QLabel()
        self._gem.setPixmap(_gem_pixmap(44))
        self._gem.setStyleSheet("background: transparent;")

        self._app_lbl = QLabel(APP_NAME)
        self._app_lbl.setObjectName("logo_label")
        self._app_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._app_lbl.setStyleSheet("color: #f39c12; background: transparent;")
        self._app_lbl.setWordWrap(True)

        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setStyleSheet(
            "color: #7f8c8d; font-size: 10px; background: transparent;")

        la.addWidget(self._gem)
        la.addWidget(self._app_lbl)
        la.addWidget(ver_lbl)
        sl.addWidget(self._logo_area)

        # ── Nav buttons ───────────────────────────────────────
        self._nav_frame = QFrame()
        self._nav_frame.setStyleSheet("background: transparent;")
        nf = QVBoxLayout(self._nav_frame)
        nf.setContentsMargins(0, 4, 0, 4)
        nf.setSpacing(0)

        self._nav_buttons: dict[str, QPushButton] = {}
        self._sales_sub_btns = []
        self._sales_sub_open = False
        self._stock_sub_btns = []
        self._stock_sub_open = False
        for label, key, letter, color in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setIcon(_nav_icon(letter, color))
            btn.setIconSize(QSize(20, 20))
            btn.setCheckable(True)
            btn.setObjectName("sidebar_btn")
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #ecf0f1;
                    border: none;
                    text-align: left;
                    padding: 11px 14px;
                    font-size: 13px;
                }
                QPushButton:hover   { background: #34495e; }
                QPushButton:checked {
                    background: #f39c12;
                    color: white;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            nf.addWidget(btn)
            self._nav_buttons[key] = btn
            if key == "invoice":
                self._build_sales_submenu(nf)
            if key == "stock_entry":
                self._build_stock_submenu(nf)

        sl.addWidget(self._nav_frame)
        sl.addStretch()

        # ── Shop info ─────────────────────────────────────────
        self._shop_lbl = QLabel()
        self._shop_lbl.setWordWrap(True)
        self._shop_lbl.setStyleSheet(
            "color: #95a5a6; font-size: 10px;"
            "background: transparent; padding: 5px 12px;")
        sl.addWidget(self._shop_lbl)

        # ── Logout ────────────────────────────────────────────
        self._btn_logout = QPushButton("  Logout")
        self._btn_logout.setIcon(_nav_icon("X", "#922b21"))
        self._btn_logout.setIconSize(QSize(20, 20))
        self._btn_logout.setStyleSheet("""
            QPushButton {
                background: #c0392b; color: white; border: none;
                padding: 12px 14px; font-size: 13px; text-align: left;
            }
            QPushButton:hover { background: #e74c3c; }
        """)
        self._btn_logout.clicked.connect(self._logout)
        sl.addWidget(self._btn_logout)

        root.addWidget(self._sidebar)

        # ══ STACKED PAGES ════════════════════════════════════
        self._stack = QStackedWidget()
        self._stack.setObjectName("content_area")
        self._pages: dict[str, QWidget] = {}

        pages = {
            "home":            HomePage(),
            "invoice":         InvoicePage(),
            "sales_datewise":  DatewiseSalesPage(),
            "sales_itemwise":  ItemSalesReportPage(),
            "invoice_history": SalesReportPage(history_mode=True),
            "stock":           StockPage(),
            "stock_entry":     StockEntryPage(),
            "stock_itemwise":   ItemwiseStockPage(),
            "stock_metalwise":  MetalwiseStockPage(),
            "stock_datewise":   DatewiseStockPage(),
            "karigar":           KarigarPage(),
            "karigar_directory": KarigarDirectoryPage(),
            "customers":         CustomerPage(),
            "settings":        SettingsPage(),
            "backup":          BackupPage(),
        }
        for key, page in pages.items():
            self._stack.addWidget(page)
            self._pages[key] = page

        root.addWidget(self._stack)
        self._switch_page("home")

        # Wire invoice edit / duplicate from report pages that support it
        inv_page = self._pages["invoice"]
        for key in ("sales_itemwise", "invoice_history"):
            p = self._pages[key]
            p.edit_invoice_requested.connect(
                lambda inv, ip=inv_page: self._open_invoice_for_edit(inv, ip)
            )
            p.duplicate_invoice_requested.connect(
                lambda inv, ip=inv_page: self._open_invoice_for_duplicate(inv, ip)
            )

        # Wire invoice edit from the home (dashboard) dues table
        self._pages["home"].edit_invoice_requested.connect(
            lambda inv, ip=inv_page: self._open_invoice_for_edit(inv, ip)
        )

        # Wire item-wise → date-wise stock navigation
        self._pages["stock_itemwise"].view_datewise_requested.connect(
            self._open_stock_datewise
        )

    _NAV_BTN_EXPANDED = """
        QPushButton {
            background: transparent; color: #ecf0f1; border: none;
            text-align: left; padding: 11px 14px; font-size: 13px;
        }
        QPushButton:hover   { background: #34495e; }
        QPushButton:checked { background: #f39c12; color: white; font-weight: bold; }
    """
    _NAV_BTN_COLLAPSED = """
        QPushButton {
            background: transparent; border: none; padding: 10px 0px;
        }
        QPushButton:hover   { background: #34495e; }
        QPushButton:checked { background: #f39c12; }
    """
    _LOGOUT_EXPANDED = """
        QPushButton {
            background: #c0392b; color: white; border: none;
            padding: 12px 14px; font-size: 13px; text-align: left;
        }
        QPushButton:hover { background: #e74c3c; }
    """
    _LOGOUT_COLLAPSED = """
        QPushButton {
            background: #c0392b; color: white; border: none; padding: 10px 0px;
        }
        QPushButton:hover { background: #e74c3c; }
    """
    _SUB_BTN_EXPANDED = """
        QPushButton {
            background: transparent; color: #aab7c4; border: none;
            text-align: left; padding: 8px 14px 8px 44px; font-size: 12px;
        }
        QPushButton:hover   { background: #34495e; color: #ecf0f1; }
        QPushButton:checked { background: #2980b9; color: white; font-weight: bold; }
    """
    _SUB_BTN_COLLAPSED = """
        QPushButton { background: transparent; border: none; padding: 8px 0px; }
        QPushButton:hover   { background: #34495e; }
        QPushButton:checked { background: #2980b9; }
    """

    # ─────────────────────────────────────────────────────────
    #  Sales Report submenu
    # ─────────────────────────────────────────────────────────
    def _build_sales_submenu(self, parent_layout):
        self._btn_sales_parent = QPushButton("  Sales Report  ▶")
        self._btn_sales_parent.setIcon(_nav_icon("S", "#2980b9"))
        self._btn_sales_parent.setIconSize(QSize(20, 20))
        self._btn_sales_parent.setCheckable(True)
        self._btn_sales_parent.setObjectName("sidebar_btn")
        self._btn_sales_parent.setStyleSheet(self._NAV_BTN_EXPANDED)
        self._btn_sales_parent.clicked.connect(self._toggle_sales_submenu)
        parent_layout.addWidget(self._btn_sales_parent)

        for sub_label, sub_key in [
            ("  ↳  Date-wise", "sales_datewise"),
            ("  ↳  Item-wise", "sales_itemwise"),
        ]:
            btn = QPushButton(sub_label)
            btn.setCheckable(True)
            btn.setVisible(False)
            btn.setObjectName("sidebar_subbtn")
            btn.setStyleSheet(self._SUB_BTN_EXPANDED)
            btn.clicked.connect(lambda _, k=sub_key: self._switch_page(k))
            parent_layout.addWidget(btn)
            self._nav_buttons[sub_key] = btn
            self._sales_sub_btns.append(btn)

    def _restore_active_checks(self):
        """Re-sync all sidebar check states to whichever page is currently visible."""
        current = self._stack.currentWidget()
        current_key = next((k for k, p in self._pages.items() if p == current), None)
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == current_key)
        self._btn_sales_parent.setChecked(
            current_key in ("sales_datewise", "sales_itemwise"))
        self._btn_stock_parent.setChecked(
            current_key in ("stock_itemwise", "stock_metalwise", "stock_datewise"))

    def _toggle_sales_submenu(self):
        self._sales_sub_open = not self._sales_sub_open
        show = self._sales_sub_open and self._sidebar_expanded
        for btn in self._sales_sub_btns:
            btn.setVisible(show)
        if self._sidebar_expanded:
            arrow = "  ▼" if self._sales_sub_open else "  ▶"
            self._btn_sales_parent.setText(f"  Sales Report{arrow}")
        self._restore_active_checks()

    # ─────────────────────────────────────────────────────────
    #  Stock Report submenu
    # ─────────────────────────────────────────────────────────
    def _build_stock_submenu(self, parent_layout):
        self._btn_stock_parent = QPushButton("  Stock Report  ▶")
        self._btn_stock_parent.setIcon(_nav_icon("R", "#d35400"))
        self._btn_stock_parent.setIconSize(QSize(20, 20))
        self._btn_stock_parent.setCheckable(True)
        self._btn_stock_parent.setObjectName("sidebar_btn")
        self._btn_stock_parent.setStyleSheet(self._NAV_BTN_EXPANDED)
        self._btn_stock_parent.clicked.connect(self._toggle_stock_submenu)
        parent_layout.addWidget(self._btn_stock_parent)

        for sub_label, sub_key in [
            ("  ↳  Item-wise",  "stock_itemwise"),
            ("  ↳  Metal-wise", "stock_metalwise"),
            ("  ↳  Date-wise",  "stock_datewise"),
        ]:
            btn = QPushButton(sub_label)
            btn.setCheckable(True)
            btn.setVisible(False)
            btn.setObjectName("sidebar_subbtn")
            btn.setStyleSheet(self._SUB_BTN_EXPANDED)
            btn.clicked.connect(lambda _, k=sub_key: self._switch_page(k))
            parent_layout.addWidget(btn)
            self._nav_buttons[sub_key] = btn
            self._stock_sub_btns.append(btn)

    def _toggle_stock_submenu(self):
        self._stock_sub_open = not self._stock_sub_open
        show = self._stock_sub_open and self._sidebar_expanded
        for btn in self._stock_sub_btns:
            btn.setVisible(show)
        if self._sidebar_expanded:
            arrow = "  ▼" if self._stock_sub_open else "  ▶"
            self._btn_stock_parent.setText(f"  Stock Report{arrow}")
        self._restore_active_checks()

    def _open_stock_datewise(self, item_name, purity, metal):
        self._switch_page("stock_datewise")   # refresh() loads entries and rebuilds combos first
        self._pages["stock_datewise"].set_item_filter(item_name, purity, metal)

    # ─────────────────────────────────────────────────────────
    #  Toggle sidebar
    # ─────────────────────────────────────────────────────────
    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        target = SIDEBAR_EXPANDED if self._sidebar_expanded else SIDEBAR_COLLAPSED

        # Animate min + max width together so the layout follows smoothly
        for prop in (b"minimumWidth", b"maximumWidth"):
            anim = QPropertyAnimation(self._sidebar, prop)
            anim.setDuration(230)
            anim.setStartValue(self._sidebar.width())
            anim.setEndValue(target)
            anim.setEasingCurve(QEasingCurve.InOutCubic)
            anim.start()
            setattr(self, f"_anim_{prop.decode()}", anim)  # keep reference alive

        expanded = self._sidebar_expanded

        # Logo area and shop label only visible when expanded
        self._logo_area.setVisible(expanded)
        self._shop_lbl.setVisible(expanded)

        # Nav buttons: show text + left-align when expanded; icon-only when collapsed
        for (label, key, _letter, _color) in NAV_ITEMS:
            btn = self._nav_buttons[key]
            btn.setText(label if expanded else "")
            btn.setStyleSheet(
                self._NAV_BTN_EXPANDED if expanded else self._NAV_BTN_COLLAPSED
            )

        # Sales Report parent button
        if expanded:
            arrow = "  ▼" if self._sales_sub_open else "  ▶"
            self._btn_sales_parent.setText(f"  Sales Report{arrow}")
        else:
            self._btn_sales_parent.setText("")
        self._btn_sales_parent.setStyleSheet(
            self._NAV_BTN_EXPANDED if expanded else self._NAV_BTN_COLLAPSED
        )

        # Sales Report sub-buttons: only visible when expanded AND submenu is open
        for btn in self._sales_sub_btns:
            btn.setVisible(expanded and self._sales_sub_open)
            btn.setStyleSheet(
                self._SUB_BTN_EXPANDED if expanded else self._SUB_BTN_COLLAPSED
            )

        # Stock Report parent button
        if expanded:
            arrow = "  ▼" if self._stock_sub_open else "  ▶"
            self._btn_stock_parent.setText(f"  Stock Report{arrow}")
        else:
            self._btn_stock_parent.setText("")
        self._btn_stock_parent.setStyleSheet(
            self._NAV_BTN_EXPANDED if expanded else self._NAV_BTN_COLLAPSED
        )

        # Stock Report sub-buttons
        for btn in self._stock_sub_btns:
            btn.setVisible(expanded and self._stock_sub_open)
            btn.setStyleSheet(
                self._SUB_BTN_EXPANDED if expanded else self._SUB_BTN_COLLAPSED
            )

        # Logout button: full label when expanded, icon-only when collapsed
        self._btn_logout.setText("  Logout" if expanded else "")
        self._btn_logout.setStyleSheet(
            self._LOGOUT_EXPANDED if expanded else self._LOGOUT_COLLAPSED
        )

        # Update toggle-button icon & tooltip
        if expanded:
            self._toggle_btn.setIcon(_arrow_icon("left", 32))
            self._toggle_btn.setToolTip("Collapse sidebar")
        else:
            self._toggle_btn.setIcon(_arrow_icon("right", 32))
            self._toggle_btn.setToolTip("Expand sidebar")

    # ─────────────────────────────────────────────────────────
    #  Page switching
    # ─────────────────────────────────────────────────────────
    def _switch_page(self, key: str):
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)
        self._btn_sales_parent.setChecked(key in ("sales_datewise", "sales_itemwise"))
        self._btn_stock_parent.setChecked(key in ("stock_itemwise", "stock_metalwise", "stock_datewise"))
        page = self._pages.get(key)
        if page:
            if hasattr(page, "refresh"):
                page.refresh()
            self._stack.setCurrentWidget(page)

    # ─────────────────────────────────────────────────────────
    #  Logout
    # ─────────────────────────────────────────────────────────
    def _logout(self):
        reply = QMessageBox.question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.logout_requested.emit()

    # ─────────────────────────────────────────────────────────
    #  Shop label / logo
    # ─────────────────────────────────────────────────────────
    def refresh_shop_label(self):
        shop = AppConfig.shop()
        shop_name = shop.get("shop_name", "").strip()
        self._shop_lbl.setText(f"{shop_name}\n{shop.get('mobile', '')}")
        self._app_lbl.setText(shop_name if shop_name else APP_NAME)

        if os.path.exists(LOGO_FILE):
            pix = QPixmap(LOGO_FILE).scaled(
                64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._gem.setPixmap(pix)
        else:
            self._gem.setPixmap(_gem_pixmap(44))

    def _open_invoice_for_edit(self, inv: dict, inv_page):
        inv_page.load_for_edit(inv)
        self._switch_page("invoice")

    def _open_invoice_for_duplicate(self, inv: dict, inv_page):
        inv_page.load_for_duplicate(inv)
        self._switch_page("invoice")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_shop_label()
