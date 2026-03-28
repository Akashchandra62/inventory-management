# ============================================================
# ui/sales_report_page.py - Sales Report / Invoice History
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QDateEdit, QGroupBox, QFrame,
    QHeaderView, QAbstractItemView, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from services.invoice_service import filter_invoices, get_all_invoices
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf
import csv, os
from datetime import date


class SalesReportPage(QWidget):
    def __init__(self, history_mode: bool = False):
        super().__init__()
        self.history_mode = history_mode
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
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
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
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
        self.tbl.setHorizontalHeaderLabels([
            "Invoice No", "Date", "Time",
            "Customer", "Mobile", "Subtotal", "Tax", "Grand Total", "Action"
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setDefaultSectionSize(42)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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
            lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
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
        self._data = self._all_invoices
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
            
        self._data = filtered
        self._populate(self._data)

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
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(r, c, cell)

            # Action button
            btn_dl = QPushButton("Download")
            btn_dl.setStyleSheet("background:#27ae60; color:white; padding: 4px 8px; border-radius:3px; font-weight:bold; font-size:11px;")
            btn_dl.clicked.connect(lambda checked, i=inv: save_invoice_as_pdf(i, parent=self))
            
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.addWidget(btn_dl)
            self.tbl.setCellWidget(r, 8, btn_container)

            total_sales += inv.get("grand_total", 0)
            total_tax   += inv.get("tax_amount", 0)

        self.lbl_count.setText(f"Invoices: {len(invoices)}")
        self.lbl_total.setText(f"Total Sales: {format_currency(total_sales)}")
        self.lbl_tax.setText(f"Total Tax: {format_currency(total_tax)}")

    def _view_invoice(self):
        row = self.tbl.currentRow()
        if row < 0 or row >= len(self._data):
            return
        inv = self._data[row]
        from ui.invoice_detail_dialog import InvoiceDetailDialog
        dlg = InvoiceDetailDialog(inv, self)
        dlg.exec()

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
        from PyQt6.QtWidgets import QFileDialog
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