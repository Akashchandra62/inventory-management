# ============================================================
# ui/stock_page.py — Current Inventory (derived from Stock Entry ledger)
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QFrame, QScrollArea,
    QHeaderView, QAbstractItemView, QComboBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from services.stock_entry_service import get_inventory


class StockPage(QWidget):
    def __init__(self):
        super().__init__()
        self._all: list[dict] = []
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

        # Title
        top = QHBoxLayout()
        title = QLabel("📦  Current Stock")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        top.addWidget(title)
        top.addStretch()
        root.addLayout(top)

        # Info hint
        info = QLabel("Stock is managed via the  Stock Entry  tab. "
                      "This view shows current inventory aggregated from all IN / OUT entries.")
        info.setStyleSheet("color:#7f8c8d; font-size:11px; padding:2px 0;")
        root.addWidget(info)

        # Filter row
        fr = QHBoxLayout()
        fr.setSpacing(8)
        fr.addWidget(QLabel("Metal:"))
        self.cmb_metal = QComboBox()
        self.cmb_metal.setMinimumHeight(32)
        self.cmb_metal.setMinimumWidth(120)
        self.cmb_metal.currentTextChanged.connect(self._apply_filter)
        fr.addWidget(self.cmb_metal)

        fr.addWidget(QLabel("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Item name / sub name…")
        self.txt_search.setMinimumHeight(32)
        self.txt_search.textChanged.connect(self._apply_filter)
        fr.addWidget(self.txt_search)
        fr.addStretch()
        root.addLayout(fr)

        # Table
        self.tbl = QTableWidget()
        _H = ["Metal", "Item Name", "Sub Name", "Purity",
              "Wt IN (g)", "Wt OUT (g)", "Current Wt (g)",
              "Qty IN", "Qty OUT", "Net Qty",
              "Location", "Last Entry"]
        self.tbl.setColumnCount(len(_H))
        self.tbl.setHorizontalHeaderLabels(_H)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        _fixed = {0: 90, 2: 100, 3: 70, 4: 90, 5: 90,
                  6: 100, 7: 65, 8: 65, 9: 65, 10: 110, 11: 90}
        for c, w in _fixed.items():
            self.tbl.setColumnWidth(c, w)
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(400)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(30)
        root.addWidget(self.tbl)

        # Summary footer
        sf = QFrame()
        sf.setStyleSheet(
            "background:white; border:1px solid #e0e0e0;"
            "border-radius:5px; padding:6px;"
        )
        sl = QHBoxLayout(sf)
        self.lbl_items  = QLabel("Items: 0")
        self.lbl_wt_in  = QLabel("Total Wt IN: 0.000 g")
        self.lbl_wt_out = QLabel("Total Wt OUT: 0.000 g")
        self.lbl_cur_wt = QLabel("Current Wt: 0.000 g")
        for lbl in (self.lbl_items, self.lbl_wt_in, self.lbl_wt_out, self.lbl_cur_wt):
            lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            lbl.setStyleSheet("background:transparent; color:#2c3e50;")
        sl.addWidget(self.lbl_items)
        sl.addStretch()
        sl.addWidget(self.lbl_wt_in)
        sl.addStretch()
        sl.addWidget(self.lbl_wt_out)
        sl.addStretch()
        sl.addWidget(self.lbl_cur_wt)
        root.addWidget(sf)

    def refresh(self):
        self._all = get_inventory()
        # Rebuild metal filter
        metals = sorted({i.get("metal_type", "") for i in self._all
                         if i.get("metal_type")})
        curr = self.cmb_metal.currentText()
        self.cmb_metal.blockSignals(True)
        self.cmb_metal.clear()
        self.cmb_metal.addItem("All")
        self.cmb_metal.addItems(metals)
        idx = self.cmb_metal.findText(curr)
        self.cmb_metal.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_metal.blockSignals(False)
        self._apply_filter()

    def _apply_filter(self):
        metal = self.cmb_metal.currentText()
        q = self.txt_search.text().strip().lower()
        data = self._all
        if metal != "All":
            data = [i for i in data if i.get("metal_type", "") == metal]
        if q:
            data = [i for i in data
                    if q in i.get("item_name", "").lower()
                    or q in i.get("sub_name",  "").lower()]
        self._populate(data)

    def _populate(self, data: list):
        self.tbl.setRowCount(0)
        ti = to = tc = 0.0
        for inv in data:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            cur_wt  = inv.get("current_wt",  0.0)
            cur_qty = inv.get("current_qty",  0)
            vals = [
                inv.get("metal_type",  ""),
                inv.get("item_name",   ""),
                inv.get("sub_name",    ""),
                inv.get("purity",      ""),
                f"{inv.get('wt_in',  0.0):.3f}",
                f"{inv.get('wt_out', 0.0):.3f}",
                f"{cur_wt:.3f}",
                str(inv.get("qty_in",  0)),
                str(inv.get("qty_out", 0)),
                str(cur_qty),
                inv.get("location",  ""),
                inv.get("last_date", ""),
            ]
            _right = {4, 5, 6, 7, 8, 9}
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(
                    Qt.AlignRight | Qt.AlignVCenter if c in _right
                    else Qt.AlignCenter
                )
                if c == 6 and cur_wt <= 0:
                    cell.setForeground(QColor("#e74c3c"))
                elif c == 9 and cur_qty <= 0:
                    cell.setForeground(QColor("#e74c3c"))
                self.tbl.setItem(r, c, cell)
            ti += inv.get("wt_in",  0.0)
            to += inv.get("wt_out", 0.0)
            tc += cur_wt

        self.lbl_items.setText(f"Items: {len(data)}")
        self.lbl_wt_in.setText(f"Total Wt IN: {ti:.3f} g")
        self.lbl_wt_out.setText(f"Total Wt OUT: {to:.3f} g")
        self.lbl_cur_wt.setText(f"Current Wt: {tc:.3f} g")
