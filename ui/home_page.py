# ============================================================
# ui/home_page.py - Dashboard Home Page
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QLineEdit, QGroupBox, QAbstractItemView,
    QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QCursor
from typing import List, Optional
from app.config import AppConfig
from services.invoice_service import get_all_invoices
from services.stock_entry_service import get_inventory
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
        self.setCursor(Qt.PointingHandCursor)
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
        val.setFont(QFont("Segoe UI", 20, QFont.Bold))
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
    edit_invoice_requested = pyqtSignal(dict)

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
        scroll.setFrameShape(QFrame.NoFrame)
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
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
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
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
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
        self._all_stock     = []  # No longer used (was from stock table)
        self._all_vendors   = get_all_vendors()
        self._all_customers = get_all_customers()

        # Get current inventory from stock_entries ledger and filter by threshold
        threshold = AppConfig.low_stock_threshold()
        inventory = get_inventory()
        self._all_low_stock = [
            item for item in inventory
            if item.get("current_qty", 0) <= threshold and (
                item.get("qty_in", 0) > 0 or item.get("qty_out", 0) > 0
            )
        ]

        today_str = date.today().isoformat()
        today_inv = [i for i in self._all_invoices if i.get("date") == today_str]
        today_sales  = sum(i.get("grand_total", 0) for i in today_inv)
        total_sales  = sum(i.get("grand_total", 0) for i in self._all_invoices)
        today_cash   = sum(float(i.get("cash_paid",  0)) for i in today_inv)
        today_upi    = sum(float(i.get("upi_paid",   0)) for i in today_inv)
        today_card   = sum(float(i.get("card_paid",  0)) for i in today_inv)
        today_cheque = sum(float(i.get("cheque_paid",0)) for i in today_inv)

        today_dues_count = len({i.get("customer_name", "") for i in today_inv
                                if float(i.get("due_amount", 0) or 0) > 0})
        total_dues_count = len({i.get("customer_name", "") for i in self._all_invoices
                                if float(i.get("due_amount", 0) or 0) > 0})

        cards_data = [
            ("today_sales",   "💰", "Today's Sales",    format_currency(today_sales),   "#f39c12"),
            ("today_cash",    "💵", "Today's Cash",     format_currency(today_cash),    "#27ae60"),
            ("today_upi",     "📲", "Today's UPI",      format_currency(today_upi),     "#2980b9"),
            ("today_card",    "💳", "Today's Card",     format_currency(today_card),    "#8e44ad"),
            ("today_cheque",  "🏦", "Today's Cheque",   format_currency(today_cheque),  "#16a085"),
            ("today_invoices","🧾", "Today's Invoices", str(len(today_inv)),            "#e67e22"),
            ("total_sales",   "📊", "Total Revenue",    format_currency(total_sales),   "#c0392b"),
            ("total_invoices","📋", "Total Invoices",   str(len(self._all_invoices)),   "#7f8c8d"),
            ("stock",         "📦", "Stock Items",      str(len(inventory)),            "#1abc9c"),
            ("customers",     "👥", "Customers",        str(len(self._all_customers)),  "#2c3e50"),
            ("vendors",       "🏪", "Vendors",          str(len(self._all_vendors)),    "#d35400"),
            ("low_stock",     "⚠️", "Low Stock",        str(len(self._all_low_stock)),  "#e74c3c"),
            ("total_dues",    "🔴", "Customers with Due",       str(total_dues_count),  "#e74c3c"),
            ("today_dues",    "📅", "Customers with Due Today",  str(today_dues_count),  "#c0392b"),
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
            "today_sales":    "Today's Sales",
            "today_cash":     "Today's Cash Payments",
            "today_upi":      "Today's UPI Payments",
            "today_card":     "Today's Card Payments",
            "today_cheque":   "Today's Cheque Payments",
            "today_invoices": "Today's Invoices",
            "total_sales":    "Total Revenue",
            "total_invoices": "Total Invoices",
            "stock":          "Stock Items",
            "vendors":        "Vendors",
            "customers":      "Customers",
            "low_stock":      "Low Stock",
            "total_dues":     "All Pending Dues",
            "today_dues":     "Today's Dues",
        }
        self.lbl_metric_title.setText(f"Showing: {titles.get(key, key)}")

        invoice_keys = {
            "today_sales", "today_cash", "today_upi", "today_card",
            "today_cheque", "today_invoices", "total_sales", "total_invoices",
            "total_dues", "today_dues",
        }
        enable = key in invoice_keys
        self.dt_from.setEnabled(enable)
        self.dt_to.setEnabled(enable)
        self.lbl_date_from.setEnabled(enable)
        self.lbl_date_to.setEnabled(enable)
            
        self._apply_filters()

    def _apply_filters(self):
        term = self.txt_search.text().strip().lower()
        d_from = self.dt_from.date().toString("yyyy-MM-dd")
        d_to = self.dt_to.date().toString("yyyy-MM-dd")
        today_str = date.today().isoformat()

        data = []
        headers = []
        _due_rows = []

        # ── Invoice / payment-mode metrics ────────────────────
        _pay_field = {
            "today_cash":   "cash_paid",
            "today_upi":    "upi_paid",
            "today_card":   "card_paid",
            "today_cheque": "cheque_paid",
        }
        _today_only = {
            "today_sales", "today_cash", "today_upi",
            "today_card", "today_cheque", "today_invoices",
        }

        if self._current_metric in (
            "today_sales", "today_invoices", "total_sales", "total_invoices",
            "today_cash", "today_upi", "today_card", "today_cheque",
            "total_dues", "today_dues",
        ):
            pay_field = _pay_field.get(self._current_metric)
            is_dues_metric = self._current_metric in ("total_dues", "today_dues")
            if pay_field:
                headers = ["Inv No", "Date", "Customer", "Mobile",
                           "Grand Total", "Cash", "UPI", "Card", "Cheque", "Due"]
            elif is_dues_metric:
                headers = ["Inv No", "Date", "Customer", "Mobile", "Grand Total", "Due Amount", "Due Date", "Action"]
            else:
                headers = ["Inv No", "Date", "Customer", "Mobile", "Grand Total"]

            _due_rows = []
            for inv in self._all_invoices:
                inv_dt = inv.get("date", "")

                if is_dues_metric:
                    due_val = float(inv.get("due_amount", 0) or 0)
                    if due_val <= 0:
                        continue
                    if self._current_metric == "today_dues" and inv_dt != today_str:
                        continue
                elif self._current_metric in _today_only:
                    if inv_dt != today_str:
                        continue
                else:
                    if not (d_from <= inv_dt <= d_to):
                        continue

                # For payment-mode cards only include invoices where that mode > 0
                if pay_field and float(inv.get(pay_field, 0)) == 0:
                    continue

                if term:
                    values = (
                        f"{inv.get('invoice_number','')} {inv.get('customer_name','')} "
                        f"{inv.get('customer_mobile','')} {inv.get('grand_total','')} {inv_dt}"
                    ).lower()
                    if term not in values:
                        continue

                if pay_field:
                    row_data = [
                        inv.get("invoice_number", ""),
                        inv_dt,
                        inv.get("customer_name", ""),
                        inv.get("customer_mobile", ""),
                        format_currency(inv.get("grand_total",   0)),
                        format_currency(inv.get("cash_paid",     0)),
                        format_currency(inv.get("upi_paid",      0)),
                        format_currency(inv.get("card_paid",     0)),
                        format_currency(inv.get("cheque_paid",   0)),
                        format_currency(inv.get("due_amount",    0)),
                    ]
                elif is_dues_metric:
                    due_date_val = inv.get("due_date", "") or ""
                    row_data = [
                        inv.get("invoice_number", ""),
                        inv_dt,
                        inv.get("customer_name", ""),
                        inv.get("customer_mobile", ""),
                        format_currency(inv.get("grand_total", 0)),
                        format_currency(inv.get("due_amount",  0)),
                        due_date_val,
                    ]
                    _due_rows.append((row_data, due_date_val == today_str, inv))
                    continue
                else:
                    row_data = [
                        inv.get("invoice_number", ""),
                        inv_dt,
                        inv.get("customer_name", ""),
                        inv.get("customer_mobile", ""),
                        format_currency(inv.get("grand_total", 0)),
                    ]
                data.append(row_data)

            if is_dues_metric:
                _due_rows.sort(key=lambda x: (not x[1], x[0][1]))
                data = [r for r, _, _ in _due_rows]
                headers = headers  # already set

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
                
        if self._current_metric in ("total_dues", "today_dues"):
            highlight = {i for i, (_, is_today, _inv) in enumerate(_due_rows) if is_today}
            self._populate_table(headers, data, highlight_rows=highlight)
            for row_idx, (_, _, inv_dict) in enumerate(_due_rows):
                btn = QPushButton("✏ Edit")
                btn.setStyleSheet(
                    "QPushButton{background:#2980b9;color:white;border-radius:3px;"
                    "padding:3px 8px;font-size:11px;font-weight:bold;}"
                    "QPushButton:hover{background:#2471a3;}"
                )
                btn.clicked.connect(lambda checked, i=inv_dict: self.edit_invoice_requested.emit(i))
                self.tbl.setCellWidget(row_idx, len(headers) - 1, btn)
        else:
            self._populate_table(headers, data)

    def _populate_table(self, headers: list, data: list, highlight_rows: set = None):
        from PyQt5.QtGui import QColor as _QColor
        self.tbl.setSortingEnabled(False)
        self.tbl.setColumnCount(len(headers))
        self.tbl.setHorizontalHeaderLabels(headers)
        self.tbl.setRowCount(0)

        if len(headers) > 0:
            self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row_idx, row_data in enumerate(data):
            self.tbl.insertRow(row_idx)
            is_highlight = highlight_rows is not None and row_idx in highlight_rows
            for col_idx, cell_value in enumerate(row_data):
                item = NumericTableItem(str(cell_value))
                item.setTextAlignment(Qt.AlignCenter)
                if is_highlight:
                    item.setBackground(_QColor("#fff3cd"))
                    item.setForeground(_QColor("#856404"))
                self.tbl.setItem(row_idx, col_idx, item)

        self.tbl.setSortingEnabled(True)
