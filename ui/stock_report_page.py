# ui/stock_report_page.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QHeaderView, QAbstractItemView, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.stock_service import get_all_stock, get_low_stock
from app.utils import format_currency
from app.config import AppConfig
import csv
from datetime import date


class StockReportPage(QWidget):
    def __init__(self):
        super().__init__()
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

        title = QLabel("📈  Stock Report")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        # Filter row
        fr = QHBoxLayout()
        fr.addWidget(QLabel("Category:"))
        self.cmb_cat = QComboBox(); self.cmb_cat.setMinimumHeight(32)
        self.cmb_cat.currentTextChanged.connect(self._apply_filter)
        fr.addWidget(self.cmb_cat)
        fr.addWidget(QLabel("Search:"))
        self.txt_s = QLineEdit(); self.txt_s.setPlaceholderText("Item name / vendor"); self.txt_s.setMinimumHeight(32)
        self.txt_s.textChanged.connect(self._apply_filter)
        fr.addWidget(self.txt_s)
        btn_low = QPushButton("⚠️  Low Stock Only")
        btn_low.setStyleSheet("background:#e74c3c; color:white; border-radius:4px; padding:6px 14px;")
        btn_low.clicked.connect(self._show_low)
        fr.addWidget(btn_low)
        btn_all = QPushButton("Show All")
        btn_all.setStyleSheet("background:#7f8c8d; color:white; border-radius:4px; padding:6px 12px;")
        btn_all.clicked.connect(self.refresh)
        fr.addWidget(btn_all)
        fr.addStretch()
        root.addLayout(fr)

        # Table
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(9)
        self.tbl.setHorizontalHeaderLabels(["Item", "Category", "Purity", "Gross(g)", "Net(g)", "Qty", "Buy Price", "Sell Price", "Vendor"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(360)
        root.addWidget(self.tbl)

        # Summary
        sf = QFrame()
        sf.setStyleSheet("background:white; border:1px solid #e0e0e0; border-radius:5px; padding:6px;")
        sl = QHBoxLayout(sf)
        self.lbl_items = QLabel("Items: 0")
        self.lbl_val   = QLabel("Stock Value: ₹ 0.00")
        for l in (self.lbl_items, self.lbl_val):
            l.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)); l.setStyleSheet("background:transparent; color:#2c3e50;")
        sl.addWidget(self.lbl_items); sl.addStretch(); sl.addWidget(self.lbl_val)
        root.addWidget(sf)

        # Export
        act = QHBoxLayout(); act.addStretch()
        btn_exp = QPushButton("📤  Export CSV")
        btn_exp.setStyleSheet("background:#27ae60; color:white; border-radius:4px; padding:8px 16px;")
        btn_exp.clicked.connect(self._export)
        act.addWidget(btn_exp)
        root.addLayout(act)

        self._all_stock: list = []

    def refresh(self):
        curr = self.cmb_cat.currentText()
        self.cmb_cat.blockSignals(True)
        self.cmb_cat.clear()
        self.cmb_cat.addItems(["All"] + AppConfig.categories())
        if curr:
            idx = self.cmb_cat.findText(curr)
            if idx >= 0: self.cmb_cat.setCurrentIndex(idx)
            else: self.cmb_cat.setCurrentIndex(0)
        self.cmb_cat.blockSignals(False)

        self._all_stock = get_all_stock()
        self._apply_filter()

    def _apply_filter(self):
        cat = self.cmb_cat.currentText()
        q   = self.txt_s.text().lower()
        data = self._all_stock
        if cat != "All":
            data = [s for s in data if s.get("category","") == cat]
        if q:
            data = [s for s in data if q in s.get("item_name","").lower() or q in s.get("vendor_name","").lower()]
        self._populate(data)

    def _show_low(self):
        self._populate(get_low_stock())

    def _populate(self, data: list):
        self.tbl.setRowCount(0)
        total_val = 0.0
        for s in data:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            qty = s.get("quantity", 0)
            val = s.get("purchase_price", 0) * qty
            total_val += val
            vals = [
                s.get("item_name",""), s.get("category",""), s.get("purity",""),
                str(s.get("gross_weight","")), str(s.get("net_weight","")),
                str(qty),
                format_currency(s.get("purchase_price",0)),
                format_currency(s.get("selling_price",0)),
                s.get("vendor_name",""),
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 5 and qty <= 2:
                    cell.setForeground(Qt.GlobalColor.red)
                self.tbl.setItem(r, c, cell)
        self.lbl_items.setText(f"Items: {len(data)}")
        self.lbl_val.setText(f"Stock Value: {format_currency(total_val)}")

    def _export(self):
        if not self._all:
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export", f"stock_report_{date.today()}.csv", "CSV (*.csv)")
        if not path: return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["item_name","category","purity","gross_weight","net_weight","quantity","purchase_price","selling_price","vendor_name"])
            w.writeheader(); [w.writerow({k: s.get(k,"") for k in w.fieldnames}) for s in self._all]
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Export", f"Saved to:\n{path}")
