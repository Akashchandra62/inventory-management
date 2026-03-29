# ============================================================
# ui/stock_page.py - Stock Management
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox,
    QGroupBox, QFrame, QHeaderView, QAbstractItemView, QScrollArea,
    QCompleter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.stock_service import get_all_stock, add_item, update_item, delete_item
from services.vendor_service import get_all_vendors
from services.item_catalog_service import get_names as get_catalog_names, ensure_item_exists
from models.stock_model import StockModel
from app.utils import unique_id, format_currency
from app.config import AppConfig


PURITIES   = ["24K", "22K", "18K", "14K", "Sterling 925", "999", "Other"]


class StockDialog(QDialog):
    def __init__(self, parent=None, item: dict = None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit Item" if item else "Add Stock Item")
        self.setMinimumWidth(480)
        self._build_ui()
        if item:
            self._populate(item)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        grp = QGroupBox("Item Details")
        form = QFormLayout(grp)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def le(ph=""): e = QLineEdit(); e.setPlaceholderText(ph); e.setMinimumHeight(32); return e
        def dspin(mx=9999999): s = QDoubleSpinBox(); s.setRange(0, mx); s.setDecimals(3); s.setMinimumHeight(32); return s
        def ispin(mx=99999): s = QSpinBox(); s.setRange(0, mx); s.setMinimumHeight(32); return s

        self.txt_name  = le("Item name *")
        _comp = QCompleter(get_catalog_names(), self)
        _comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        _comp.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.txt_name.setCompleter(_comp)
        # When a catalog item is selected auto-fill category
        _comp.activated.connect(self._on_catalog_selected)

        self.cmb_cat   = QComboBox(); self.cmb_cat.addItems(AppConfig.categories()); self.cmb_cat.setMinimumHeight(32)
        self.cmb_pur   = QComboBox(); self.cmb_pur.addItems(PURITIES);   self.cmb_pur.setMinimumHeight(32)
        self.spn_gross = dspin(); self.spn_gross.setSuffix(" g")
        self.spn_net   = dspin(); self.spn_net.setSuffix(" g")
        self.spn_qty   = ispin()
        self.spn_buy   = dspin(); self.spn_buy.setPrefix("₹ ")
        self.spn_sell  = dspin(); self.spn_sell.setPrefix("₹ ")
        self.cmb_vend  = QComboBox(); self.cmb_vend.setMinimumHeight(32)
        self.txt_rem   = le("Optional remarks")

        # Populate vendor dropdown
        vendors = get_all_vendors()
        self.cmb_vend.addItem("-- None --", "")
        for v in vendors:
            self.cmb_vend.addItem(v.get("vendor_name",""), v.get("vendor_id",""))

        form.addRow("Item Name *", self.txt_name)
        form.addRow("Category",    self.cmb_cat)
        form.addRow("Purity",      self.cmb_pur)
        form.addRow("Gross Weight", self.spn_gross)
        form.addRow("Net Weight",  self.spn_net)
        form.addRow("Quantity",    self.spn_qty)
        form.addRow("Buy Price",   self.spn_buy)
        form.addRow("Sell Price",  self.spn_sell)
        form.addRow("Vendor",      self.cmb_vend)
        form.addRow("Remarks",     self.txt_rem)
        root.addWidget(grp)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        btn_save = QPushButton("💾  Save")
        btn_save.setStyleSheet("background:#27ae60; color:white; border-radius:4px; padding:8px 22px;")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background:#7f8c8d; color:white; border-radius:4px; padding:8px 16px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_save); btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

    def _on_catalog_selected(self, name: str):
        from services.item_catalog_service import get_item_by_name
        entry = get_item_by_name(name)
        if entry and entry.get("category"):
            idx = self.cmb_cat.findText(entry["category"])
            if idx >= 0:
                self.cmb_cat.setCurrentIndex(idx)

    def _populate(self, item: dict):
        self.txt_name.setText(item.get("item_name",""))
        idx = self.cmb_cat.findText(item.get("category",""))
        if idx >= 0: self.cmb_cat.setCurrentIndex(idx)
        idx = self.cmb_pur.findText(item.get("purity",""))
        if idx >= 0: self.cmb_pur.setCurrentIndex(idx)
        self.spn_gross.setValue(item.get("gross_weight", 0))
        self.spn_net.setValue(item.get("net_weight", 0))
        self.spn_qty.setValue(item.get("quantity", 0))
        self.spn_buy.setValue(item.get("purchase_price", 0))
        self.spn_sell.setValue(item.get("selling_price", 0))
        self.txt_rem.setText(item.get("remarks",""))

    def _save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Item name is required.")
            return
        self.result_data = {
            "item_name":      self.txt_name.text().strip(),
            "category":       self.cmb_cat.currentText(),
            "purity":         self.cmb_pur.currentText(),
            "gross_weight":   self.spn_gross.value(),
            "net_weight":     self.spn_net.value(),
            "quantity":       self.spn_qty.value(),
            "purchase_price": self.spn_buy.value(),
            "selling_price":  self.spn_sell.value(),
            "vendor_name":    self.cmb_vend.currentText() if self.cmb_vend.currentIndex() > 0 else "",
            "remarks":        self.txt_rem.text().strip(),
        }
        # Auto-add to item catalog if name is new
        ensure_item_exists(self.result_data["item_name"], self.result_data["category"])
        self.accept()


class StockPage(QWidget):
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

        # Title + buttons
        top = QHBoxLayout()
        title = QLabel("📦  Stock Management")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn_add = QPushButton("➕  Add Item")
        btn_add.setStyleSheet("background:#27ae60; color:white; border-radius:4px; padding:8px 16px;")
        btn_add.clicked.connect(self._add)
        top.addWidget(title); top.addStretch(); top.addWidget(btn_add)
        root.addLayout(top)

        # Search
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit(); self.txt_search.setPlaceholderText("Search by name, category or vendor...")
        self.txt_search.setMinimumHeight(34); self.txt_search.textChanged.connect(self._do_search)
        search_row.addWidget(QLabel("🔍")); search_row.addWidget(self.txt_search)
        root.addLayout(search_row)

        # Table
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(10)
        self.tbl.setHorizontalHeaderLabels([
            "ID", "Item Name", "Category", "Purity",
            "Gross(g)", "Net(g)", "Qty", "Buy Price", "Sell Price", "Vendor"
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(380)
        root.addWidget(self.tbl)

        # Action buttons
        act = QHBoxLayout(); act.addStretch()
        btn_edit = QPushButton("✏️  Edit"); btn_edit.setStyleSheet("background:#2980b9; color:white; border-radius:4px; padding:8px 16px;"); btn_edit.clicked.connect(self._edit)
        btn_del  = QPushButton("🗑  Delete"); btn_del.setStyleSheet("background:#e74c3c; color:white; border-radius:4px; padding:8px 16px;"); btn_del.clicked.connect(self._delete)
        act.addWidget(btn_edit); act.addWidget(btn_del)
        root.addLayout(act)

        self._all_stock: list[dict] = []

    def refresh(self):
        self._all_stock = get_all_stock()
        self._populate(self._all_stock)

    def _do_search(self, text: str):
        q = text.lower()
        filtered = [s for s in self._all_stock if
                    q in s.get("item_name","").lower() or
                    q in s.get("category","").lower() or
                    q in s.get("vendor_name","").lower()]
        self._populate(filtered)

    def _populate(self, data: list):
        self.tbl.setRowCount(0)
        for item in data:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            vals = [
                item.get("item_id",""), item.get("item_name",""),
                item.get("category",""), item.get("purity",""),
                str(item.get("gross_weight","")), str(item.get("net_weight","")),
                str(item.get("quantity","")),
                format_currency(item.get("purchase_price",0)),
                format_currency(item.get("selling_price",0)),
                item.get("vendor_name",""),
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Highlight low stock
                if c == 6 and item.get("quantity", 1) <= 2:
                    cell.setForeground(Qt.GlobalColor.red)
                self.tbl.setItem(r, c, cell)
        self.tbl.setColumnHidden(0, True)

    def _add(self):
        dlg = StockDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            s = StockModel(**dlg.result_data)
            add_item(s)
            self.refresh()

    def _edit(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Select a row first."); return
        # Find item
        item_id = self.tbl.item(row, 0).text()
        item = next((s for s in self._all_stock if s.get("item_id") == item_id), None)
        if not item: return
        dlg = StockDialog(self, item=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            update_item(item_id, dlg.result_data)
            self.refresh()

    def _delete(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete", "Select a row first."); return
        item_id = self.tbl.item(row, 0).text()
        name    = self.tbl.item(row, 1).text()
        reply = QMessageBox.question(self, "Delete", f"Delete '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_item(item_id)
            self.refresh()
