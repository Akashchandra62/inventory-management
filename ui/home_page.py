# ============================================================
# ui/home_page.py - Dashboard Home Page
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QLineEdit, QGroupBox, QAbstractItemView,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QCursor
from app.config import AppConfig
from services.invoice_service import get_all_invoices
from services.stock_service import get_all_stock, get_low_stock
from services.vendor_service import get_all_vendors
from services.customer_service import get_all_customers
from app.utils import format_currency
from datetime import date, datetime


class NumericTableItem(QTableWidgetItem):
    """Custom table item to correctly sort numbers and currency."""
    def __lt__(self, other):
        try:
            val1 = float(self.text().replace("₹", "").replace(",", "").strip())
            val2 = float(other.text().replace("₹", "").replace(",", "").strip())
            return val1 < val2
        except ValueError:
            return super().__lt__(other)


class StatCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, key: str, icon: str, title: str, value: str, color: str = "#2c3e50"):
        super().__init__()
        self.key = key
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("stat_card")
        self.setStyleSheet(f"""
            QFrame#stat_card {{
                background: white;
                border-radius: 8px;
                border-left: 5px solid {color};
                border-top: 1px solid #e0e0e0;
                border-right: 1px solid #e0e0e0;
                border-bottom: 1px solid #e0e0e0;
            }}
            QFrame#stat_card:hover {{
                background: #fdfefe;
                border-right: 1px solid #bdc3c7;
                border-bottom: 1px solid #bdc3c7;
            }}
        """)
        self.setMinimumHeight(110)
        cl = QVBoxLayout(self)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        ico = QLabel(icon)
        ico.setFont(QFont("Segoe UI", 22))
        ico.setStyleSheet("background: transparent; border: none;")

        val = QLabel(value)
        val.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        val.setStyleSheet(f"color: {color}; background: transparent; border: none;")

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #7f8c8d; font-size: 11px; background: transparent; border: none;")

        cl.addWidget(ico)
        cl.addWidget(val)
        cl.addWidget(lbl)

    def mousePressEvent(self, event):
        self.clicked.emit(self.key)
        super().mousePressEvent(event)


class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self._current_metric = "today_sales"
        self._all_invoices = []
        self._all_stock = []
        self._all_vendors = []
        self._all_customers = []
        self._all_low_stock = []
        self._build_ui()

    def _build_ui(self):
        self.setObjectName("content_area")
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Page title
        today = date.today().strftime("%d %B %Y")
        shop  = AppConfig.shop().get("shop_name", "Jewelry Shop")
        title = QLabel(f"Dashboard – {shop}")
        title.setObjectName("page_title")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        dt_lbl = QLabel(today)
        dt_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px;")

        layout.addWidget(title)
        layout.addWidget(dt_lbl)

        # Stat cards
        self._grid = QGridLayout()
        self._grid.setSpacing(16)
        layout.addLayout(self._grid)

        # Low stock warning area
        self._warn_frame = QFrame()
        self._warn_frame.setStyleSheet(
            "QFrame { background: #fef9e7; border: 1px solid #f39c12;"
            " border-radius: 6px; padding: 8px; }"
        )
        warn_layout = QVBoxLayout(self._warn_frame)
        warn_layout.setContentsMargins(12, 10, 12, 10)
        self._warn_lbl = QLabel()
        self._warn_lbl.setWordWrap(True)
        self._warn_lbl.setStyleSheet(
            "color: #e67e22; font-size: 12px; background: transparent;"
        )
        warn_layout.addWidget(self._warn_lbl)
        layout.addWidget(self._warn_frame)

        # ── Data Table & Filter Section ──────────────────────────
        self._filter_grp = QGroupBox("Metric Data Details")
        self._filter_grp.setStyleSheet("""
            QGroupBox { 
                font-size: 14px; font-weight: bold; color: #2c3e50; 
                margin-top: 15px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 5px; 
            }
        """)
        fl = QHBoxLayout(self._filter_grp)
        fl.setContentsMargins(15, 20, 15, 15)
        fl.setSpacing(10)
        
        self.lbl_date_from = QLabel("Date From:")
        self.lbl_date_from.setStyleSheet("font-weight: normal; font-size: 13px;")
        fl.addWidget(self.lbl_date_from)
        self.dt_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setMinimumHeight(32)
        fl.addWidget(self.dt_from)

        self.lbl_date_to = QLabel("Date To:")
        self.lbl_date_to.setStyleSheet("font-weight: normal; font-size: 13px;")
        fl.addWidget(self.lbl_date_to)
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setMinimumHeight(32)
        fl.addWidget(self.dt_to)

        search_lbl = QLabel("Search:")
        search_lbl.setStyleSheet("font-weight: normal; font-size: 13px;")
        fl.addWidget(search_lbl)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search any column...")
        self.txt_search.setMinimumHeight(32)
        self.txt_search.setMaximumWidth(200)
        self.txt_search.textChanged.connect(self._apply_filters)
        self.txt_search.setStyleSheet("font-weight: normal; font-size: 13px; padding: 4px;")
        fl.addWidget(self.txt_search)

        btn_filter = QPushButton("Apply Filter")
        btn_filter.setStyleSheet(
            "QPushButton { background: #2980b9; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background: #2471a3; }"
        )
        btn_filter.clicked.connect(self._apply_filters)
        fl.addWidget(btn_filter)
        fl.addStretch()

        self.lbl_metric_title = QLabel(f"Showing: Today's Sales")
        self.lbl_metric_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #16a085;")
        fl.addWidget(self.lbl_metric_title)

        layout.addWidget(self._filter_grp)

        self.tbl = QTableWidget()
        self.tbl.setMinimumHeight(350)
        self.tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        layout.addWidget(self.tbl)

        layout.addStretch()

        self._cards: list[QFrame] = []

    def refresh(self):
        # Clear old cards
        for c in self._cards:
            self._grid.removeWidget(c)
            c.deleteLater()
        self._cards.clear()

        self._all_invoices  = get_all_invoices()
        self._all_stock     = get_all_stock()
        self._all_vendors   = get_all_vendors()
        self._all_customers = get_all_customers()
        self._all_low_stock = get_low_stock()

        today_str = date.today().isoformat()
        today_inv = [i for i in self._all_invoices if i.get("date") == today_str]
        today_sales = sum(i.get("grand_total", 0) for i in today_inv)
        total_sales = sum(i.get("grand_total", 0) for i in self._all_invoices)

        cards_data = [
            ("today_sales", "💰", "Today's Sales",    format_currency(today_sales), "#f39c12"),
            ("total_sales", "📊", "Total Revenue",    format_currency(total_sales), "#27ae60"),
            ("today_invoices", "🧾", "Today's Invoices", str(len(today_inv)),          "#2980b9"),
            ("total_invoices", "🧾", "Total Invoices",   str(len(self._all_invoices)),           "#8e44ad"),
            ("stock", "📦", "Stock Items",      str(len(self._all_stock)),              "#16a085"),
            ("vendors", "🏪", "Vendors",          str(len(self._all_vendors)),            "#2c3e50"),
            ("customers", "👥", "Customers",        str(len(self._all_customers)),          "#c0392b"),
            ("low_stock", "⚠️", "Low Stock",        str(len(self._all_low_stock)),          "#e74c3c"),
        ]

        for idx, (key, icon, title, val, color) in enumerate(cards_data):
            card = StatCard(key, icon, title, val, color)
            card.clicked.connect(self._on_card_clicked)
            row, col = divmod(idx, 4)
            self._grid.addWidget(card, row, col)
            self._cards.append(card)

        # Low stock warning
        if self._all_low_stock:
            names = ", ".join(s.get("item_name", "") for s in self._all_low_stock[:5])
            self._warn_lbl.setText(f"⚠️  Low Stock Alert: {names}" +
                                   (f" and {len(self._all_low_stock)-5} more..." if len(self._all_low_stock) > 5 else ""))
            self._warn_frame.show()
        else:
            self._warn_frame.hide()
            
        self._apply_filters()

    def _on_card_clicked(self, key: str):
        self._current_metric = key
        titles = {
            "today_sales": "Today's Sales",
            "total_sales": "Total Revenue",
            "today_invoices": "Today's Invoices",
            "total_invoices": "Total Invoices",
            "stock": "Stock Items",
            "vendors": "Vendors",
            "customers": "Customers",
            "low_stock": "Low Stock"
        }
        self.lbl_metric_title.setText(f"Showing: {titles.get(key, key)}")
        
        # Enable dates for sales/invoices, otherwise disable
        if key in ["today_sales", "total_sales", "today_invoices", "total_invoices"]:
            self.dt_from.setEnabled(True)
            self.dt_to.setEnabled(True)
            self.lbl_date_from.setEnabled(True)
            self.lbl_date_to.setEnabled(True)
        else:
            self.dt_from.setEnabled(False)
            self.dt_to.setEnabled(False)
            self.lbl_date_from.setEnabled(False)
            self.lbl_date_to.setEnabled(False)
            
        self._apply_filters()

    def _apply_filters(self):
        term = self.txt_search.text().strip().lower()
        d_from = self.dt_from.date().toString("yyyy-MM-dd")
        d_to = self.dt_to.date().toString("yyyy-MM-dd")
        today_str = date.today().isoformat()
        
        data = []
        headers = []

        if self._current_metric in ["today_sales", "total_sales", "today_invoices", "total_invoices"]:
            headers = ["Inv No", "Date", "Customer", "Mobile", "Grand Total"]
            for inv in self._all_invoices:
                inv_dt = inv.get("date", "")
                
                if self._current_metric in ["today_sales", "today_invoices"]:
                    if inv_dt != today_str: continue
                else:
                    if not (d_from <= inv_dt <= d_to): continue
                
                if term:
                    values = f"{inv.get('invoice_number','')} {inv.get('customer_name','')} {inv.get('customer_mobile','')} {inv.get('grand_total','')} {inv_dt}".lower()
                    if term not in values: continue
                    
                row_data = [
                    inv.get("invoice_number", ""),
                    inv_dt,
                    inv.get("customer_name", ""),
                    inv.get("customer_mobile", ""),
                    format_currency(inv.get("grand_total", 0))
                ]
                data.append(row_data)

        elif self._current_metric in ["stock", "low_stock"]:
            headers = ["Item Name", "Category", "Quantity", "Weight (g)", "Cost Price", "Selling Price"]
            stock_list = self._all_low_stock if self._current_metric == "low_stock" else self._all_stock
            for item in stock_list:
                if term:
                    values = f"{item.get('item_name','')} {item.get('category','')} {item.get('quantity','')} {item.get('weight_g','')} {item.get('selling_price','')} {item.get('cost_price','')}".lower()
                    if term not in values: continue
                row_data = [
                    item.get("item_name", ""),
                    item.get("category", ""),
                    str(item.get("quantity", 0)),
                    str(item.get("weight_g", "")),
                    format_currency(item.get("cost_price", 0)),
                    format_currency(item.get("selling_price", 0))
                ]
                data.append(row_data)

        elif self._current_metric == "vendors":
            headers = ["Name", "Contact Person", "Mobile", "GST No", "City"]
            for v in self._all_vendors:
                if term:
                    values = f"{v.get('vendor_name','')} {v.get('contact_person','')} {v.get('mobile','')} {v.get('gst_no','')} {v.get('city','')}".lower()
                    if term not in values: continue
                row_data = [
                    v.get("vendor_name", ""),
                    v.get("contact_person", ""),
                    v.get("mobile", ""),
                    v.get("gst_no", ""),
                    v.get("city", "")
                ]
                data.append(row_data)

        elif self._current_metric == "customers":
            headers = ["Name", "Mobile", "Email", "Address"]
            for c in self._all_customers:
                if term:
                    values = f"{c.get('customer_name','')} {c.get('mobile','')} {c.get('email','')} {c.get('address','')}".lower()
                    if term not in values: continue
                row_data = [
                    c.get("customer_name", ""),
                    c.get("mobile", ""),
                    c.get("email", ""),
                    c.get("address", "")
                ]
                data.append(row_data)
                
        self._populate_table(headers, data)

    def _populate_table(self, headers: list, data: list):
        self.tbl.setSortingEnabled(False)
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setRowCount(0)
        
        if len(headers) > 0:
            self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for row_idx, row_data in enumerate(data):
            self.tbl.insertRow(row_idx)
            for col_idx, cell_value in enumerate(row_data):
                item = NumericTableItem(str(cell_value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(row_idx, col_idx, item)
                
        self.tbl.setSortingEnabled(True)
