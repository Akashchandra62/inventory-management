# ============================================================
# ui/sales_report_page.py - Sales Report / Invoice History
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QGroupBox, QFrame,
    QHeaderView, QAbstractItemView, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from services.invoice_service import filter_invoices, get_all_invoices
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf
import csv, os
from datetime import date


_RPT_LABELS = [
    "Invoice No", "Date", "Time",
    "Customer", "Mobile", "Subtotal", "Tax", "Grand Total", "Action"
]
_RPT_HEADERS = [
    "Invoice No ▲▼", "Date ▲▼", "Time ▲▼",
    "Customer ▲▼", "Mobile ▲▼", "Subtotal ▲▼", "Tax ▲▼", "Grand Total ▲▼", "Action"
]
# col index → invoice dict key (for sorting)
_RPT_SORT_KEYS = {
    0: "invoice_number", 1: "date", 2: "time",
    3: "customer_name",  4: "customer_mobile",
    5: "subtotal",       6: "tax_amount", 7: "grand_total",
}


class SalesReportPage(QWidget):
    def __init__(self, history_mode: bool = False):
        super().__init__()
        self.history_mode = history_mode
        self._sort_col = -1   # -1 = no sort
        self._sort_asc = True
        self._data_base: list[dict] = []   # unsorted current data
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        root = QVBoxLayout(container)
        root.setContentsMargins(25, 20, 25, 20)
        root.setSpacing(14)

        page_title = "📋  Invoice History" if self.history_mode else "📊  Sales Report"
        title = QLabel(page_title)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        root.addWidget(title)

        # ── Filters ───────────────────────────────────────────
        filter_grp = QGroupBox("Filter")
        fl = QHBoxLayout(filter_grp)
        fl.setSpacing(10)

        fl.addWidget(QLabel("From:"))
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_from.setCalendarPopup(True); self.dt_from.setMinimumHeight(32)
        fl.addWidget(self.dt_from)

        fl.addWidget(QLabel("To:"))
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True); self.dt_to.setMinimumHeight(32)
        fl.addWidget(self.dt_to)

        fl.addWidget(QLabel("Customer:"))
        self.txt_cust = QLineEdit()
        self.txt_cust.setPlaceholderText("Name search")
        self.txt_cust.setMinimumHeight(32)
        self.txt_cust.setMaximumWidth(180)
        self.txt_cust.textChanged.connect(self._on_search_text_changed)
        fl.addWidget(self.txt_cust)

        fl.addWidget(QLabel("Invoice No:"))
        self.txt_inv = QLineEdit()
        self.txt_inv.setPlaceholderText("e.g. JB-0001")
        self.txt_inv.setMinimumHeight(32)
        self.txt_inv.setMaximumWidth(140)
        self.txt_inv.textChanged.connect(self._on_search_text_changed)
        fl.addWidget(self.txt_inv)

        btn_search = QPushButton("🔍  Search")
        btn_search.setStyleSheet(
            "QPushButton { background:#2980b9; color:white; border-radius:4px; padding:6px 14px; }"
            "QPushButton:hover { background:#2471a3; }"
        )
        btn_search.clicked.connect(self._do_search)
        fl.addWidget(btn_search)

        btn_all = QPushButton("Show All")
        btn_all.setStyleSheet(
            "QPushButton { background:#7f8c8d; color:white; border-radius:4px; padding:6px 14px; }"
        )
        btn_all.clicked.connect(self._show_all)
        fl.addWidget(btn_all)

        fl.addStretch()
        root.addWidget(filter_grp)

        # ── Table ─────────────────────────────────────────────
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(9)
        self.tbl.setHorizontalHeaderLabels(_RPT_HEADERS)
        self.tbl.horizontalHeader().sectionClicked.connect(self._on_header_click)
        self.tbl.horizontalHeader().setCursor(Qt.PointingHandCursor)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl.verticalHeader().setDefaultSectionSize(42)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(320)
        self.tbl.doubleClicked.connect(self._view_invoice)
        root.addWidget(self.tbl)

        # ── Summary Row ───────────────────────────────────────
        summary = QFrame()
        summary.setStyleSheet("QFrame { background:white; border:1px solid #e0e0e0; border-radius:5px; padding:6px; }")
        sl = QHBoxLayout(summary)
        self.lbl_count  = QLabel("Invoices: 0")
        self.lbl_total  = QLabel("Total Sales: ₹ 0.00")
        self.lbl_tax    = QLabel("Total Tax: ₹ 0.00")
        for lbl in (self.lbl_count, self.lbl_total, self.lbl_tax):
            lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
            lbl.setStyleSheet("color: #2c3e50; background: transparent;")
        sl.addWidget(self.lbl_count)
        sl.addStretch()
        sl.addWidget(self.lbl_total)
        sl.addSpacing(30)
        sl.addWidget(self.lbl_tax)
        root.addWidget(summary)

        # ── Action buttons ────────────────────────────────────
        act = QHBoxLayout()
        act.addStretch()
        btn_print = QPushButton("🖨  Print Invoice")
        btn_print.setStyleSheet("QPushButton { background:#f39c12; color:white; border-radius:4px; padding:8px 16px; }"
                                "QPushButton:hover { background:#e67e22; }")
        btn_print.clicked.connect(self._reprint)
        act.addWidget(btn_print)

        btn_export = QPushButton("📤  Export CSV")
        btn_export.setStyleSheet("QPushButton { background:#27ae60; color:white; border-radius:4px; padding:8px 16px; }"
                                 "QPushButton:hover { background:#229954; }")
        btn_export.clicked.connect(self._export_csv)
        act.addWidget(btn_export)
        root.addLayout(act)

        self._data: list[dict] = []

    def refresh(self):
        self._show_all()

    def _show_all(self):
        self._all_invoices = get_all_invoices()
        self._data_base = self._all_invoices
        self._data = self._apply_sort(self._data_base)
        self._populate(self._data)

    def _on_search_text_changed(self, text):
        if len(text.strip()) >= 3 or len(text.strip()) == 0:
            self._do_search()

    def _do_search(self):
        cust_term = self.txt_cust.text().strip().lower()
        inv_term = self.txt_inv.text().strip().lower()
        d_from = self.dt_from.date().toString("yyyy-MM-dd")
        d_to = self.dt_to.date().toString("yyyy-MM-dd")
        
        filtered = []
        for inv in self._all_invoices:
            inv_dt = inv.get("date", "")
            if not (d_from <= inv_dt <= d_to): continue
            
            if cust_term and cust_term not in inv.get('customer_name', '').lower() and cust_term not in inv.get('customer_mobile', ''):
                continue
            if inv_term and inv_term not in inv.get('invoice_number', '').lower():
                continue
                
            filtered.append(inv)
            
        self._data_base = filtered
        self._data = self._apply_sort(self._data_base)
        self._populate(self._data)

    # ── Column sort ───────────────────────────────────────────
    def _on_header_click(self, col: int):
        if col == 8:   # Action column — not sortable
            return
        if self._sort_col == col:
            if not self._sort_asc:
                self._sort_asc = True                  # desc → asc
            else:
                self._sort_col = -1                    # asc → remove
                self._refresh_sort_headers()
                self._data = list(self._data_base)
                self._populate(self._data)
                return
        else:
            self._sort_col = col
            self._sort_asc = False                     # first click → descending

        self._refresh_sort_headers()
        self._data = self._apply_sort(self._data_base)
        self._populate(self._data)

    def _apply_sort(self, data: list) -> list:
        if self._sort_col < 0 or self._sort_col not in _RPT_SORT_KEYS:
            return list(data)
        key = _RPT_SORT_KEYS[self._sort_col]
        def _k(inv):
            v = inv.get(key, "")
            try:    return (0, float(v))
            except: return (1, str(v).lower())
        return sorted(data, key=_k, reverse=not self._sort_asc)

    def _refresh_sort_headers(self):
        for i, lbl in enumerate(_RPT_LABELS):
            item = self.tbl.horizontalHeaderItem(i)
            if item:
                if i == self._sort_col:
                    item.setText(lbl + (" ▲" if self._sort_asc else " ▼"))
                elif i == 8:
                    item.setText(lbl)       # Action column — no sort indicator
                else:
                    item.setText(lbl + " ▲▼")

    def _populate(self, invoices: list):
        self.tbl.setRowCount(0)
        total_sales = total_tax = 0.0
        for inv in invoices:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            vals = [
                inv.get("invoice_number", ""),
                inv.get("date", ""),
                inv.get("time", ""),
                inv.get("customer_name", ""),
                inv.get("customer_mobile", ""),
                format_currency(inv.get("subtotal", 0)),
                format_currency(inv.get("tax_amount", 0)),
                format_currency(inv.get("grand_total", 0)),
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                self.tbl.setItem(r, c, cell)

            # Action buttons: View + Download
            btn_view = QPushButton("View")
            btn_view.setStyleSheet(
                "background:#2980b9;color:white;padding:4px 8px;"
                "border-radius:3px;font-weight:bold;font-size:11px;border:none;")
            btn_view.clicked.connect(lambda checked, i=inv: self._open_detail(i))

            btn_dl = QPushButton("PDF")
            btn_dl.setStyleSheet(
                "background:#27ae60;color:white;padding:4px 8px;"
                "border-radius:3px;font-weight:bold;font-size:11px;border:none;")
            btn_dl.clicked.connect(lambda checked, i=inv: save_invoice_as_pdf(i, parent=self))

            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.addWidget(btn_view)
            btn_layout.addWidget(btn_dl)
            self.tbl.setCellWidget(r, 8, btn_container)

            total_sales += inv.get("grand_total", 0)
            total_tax   += inv.get("tax_amount", 0)

        self.lbl_count.setText(f"Invoices: {len(invoices)}")
        self.lbl_total.setText(f"Total Sales: {format_currency(total_sales)}")
        self.lbl_tax.setText(f"Total Tax: {format_currency(total_tax)}")

    def _open_detail(self, inv: dict):
        from ui.invoice_detail_dialog import InvoiceDetailDialog
        dlg = InvoiceDetailDialog(inv, self)
        dlg.exec()

    def _view_invoice(self):
        row = self.tbl.currentRow()
        if row < 0 or row >= len(self._data):
            return
        self._open_detail(self._data[row])

    def _reprint(self):
        row = self.tbl.currentRow()
        if row < 0 or row >= len(self._data):
            QMessageBox.information(self, "Print", "Select an invoice row first.")
            return
        inv = self._data[row]
        save_invoice_as_pdf(inv, parent=self)

    def _export_csv(self):
        if not self._data:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", f"sales_report_{date.today()}.csv", "CSV Files (*.csv)"
        )
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "invoice_number","date","time","customer_name",
                    "customer_mobile","subtotal","tax_amount","grand_total"
                ])
                writer.writeheader()
                for inv in self._data:
                    writer.writerow({k: inv.get(k,"") for k in writer.fieldnames})
            QMessageBox.information(self, "Export", f"Exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))