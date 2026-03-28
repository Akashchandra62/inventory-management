# ui/vendor_report_page.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QHeaderView, QAbstractItemView, QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.vendor_service import get_all_vendors
from services.stock_service import get_all_stock


class VendorReportPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(scroll)
        container = QWidget(); scroll.setWidget(container)
        root = QVBoxLayout(container); root.setContentsMargins(25,20,25,20); root.setSpacing(14)

        title = QLabel("📑  Vendor Report"); title.setFont(QFont("Segoe UI",16,QFont.Weight.Bold))
        root.addWidget(title)

        sr = QHBoxLayout()
        self.txt_s = QLineEdit(); self.txt_s.setPlaceholderText("Search vendor..."); self.txt_s.setMinimumHeight(34); self.txt_s.textChanged.connect(self._search)
        sr.addWidget(QLabel("🔍")); sr.addWidget(self.txt_s); root.addLayout(sr)

        # Vendor list (top)
        vlbl = QLabel("Vendors"); vlbl.setStyleSheet("font-weight:bold; font-size:13px;")
        root.addWidget(vlbl)
        self.tbl_v = QTableWidget(); self.tbl_v.setColumnCount(5)
        self.tbl_v.setHorizontalHeaderLabels(["Name","Phone","Address","GST","Email"])
        self.tbl_v.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_v.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_v.setAlternatingRowColors(True); self.tbl_v.setMaximumHeight(220)
        self.tbl_v.selectionModel().selectionChanged.connect(self._vendor_selected)
        root.addWidget(self.tbl_v)

        # Stock by vendor (bottom)
        slbl = QLabel("Stock Supplied by Selected Vendor"); slbl.setStyleSheet("font-weight:bold; font-size:13px;")
        root.addWidget(slbl)
        self.tbl_s = QTableWidget(); self.tbl_s.setColumnCount(6)
        self.tbl_s.setHorizontalHeaderLabels(["Item","Category","Purity","Net(g)","Qty","Sell Price"])
        self.tbl_s.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_s.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_s.setAlternatingRowColors(True); self.tbl_s.setMinimumHeight(180)
        root.addWidget(self.tbl_s)
        self._all_v = []; self._all_s = []

    def refresh(self):
        self._all_v = get_all_vendors(); self._all_s = get_all_stock()
        self._populate_vendors(self._all_v)

    def _search(self, text):
        q = text.lower()
        self._populate_vendors([v for v in self._all_v if q in v.get("vendor_name","").lower()])

    def _populate_vendors(self, data):
        self.tbl_v.setRowCount(0)
        for v in data:
            r = self.tbl_v.rowCount(); self.tbl_v.insertRow(r)
            for c, key in enumerate(["vendor_name","phone","address","gst_number","email"]):
                cell = QTableWidgetItem(str(v.get(key,""))); cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_v.setItem(r,c,cell)

    def _vendor_selected(self):
        row = self.tbl_v.currentRow()
        if row < 0: self.tbl_s.setRowCount(0); return
        name = self.tbl_v.item(row,0).text()
        items = [s for s in self._all_s if s.get("vendor_name","").lower() == name.lower()]
        self.tbl_s.setRowCount(0)
        for s in items:
            r = self.tbl_s.rowCount(); self.tbl_s.insertRow(r)
            from app.utils import format_currency
            vals = [s.get("item_name",""),s.get("category",""),s.get("purity",""),
                    str(s.get("net_weight","")),str(s.get("quantity","")),format_currency(s.get("selling_price",0))]
            for c,v in enumerate(vals):
                cell = QTableWidgetItem(v); cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_s.setItem(r,c,cell)
