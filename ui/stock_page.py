# ============================================================
# ui/stock_page.py - Stock Management
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox,
    QGroupBox, QFrame, QHeaderView, QAbstractItemView, QScrollArea,
    QCompleter, QDialogButtonBox, QMenu
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QAction
from services.stock_service import get_all_stock, add_item, update_item, delete_item
from services.vendor_service import get_all_vendors
from services.item_catalog_service import get_names as get_catalog_names, ensure_item_exists
from models.stock_model import StockModel
from app.utils import unique_id, format_currency
from app.config import AppConfig


PURITIES = ["24K", "22K", "18K", "14K", "Sterling 925", "999", "Other"]

# Fixed column count (including hidden ID col at index 0)
FIXED_COLS = 10


# ── Manage Custom Columns Dialog ──────────────────────────────
class ManageColumnsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Custom Columns")
        self.setMinimumWidth(460)
        self.setMinimumHeight(380)
        self._columns = [dict(c) for c in AppConfig.custom_stock_columns()]
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        root.addWidget(QLabel(
            "Add custom columns that will appear in the stock table.\n"
            "Each item will have an input field for every column you add."
        ))

        # ── Existing columns list ──────────────────────────────
        grp = QGroupBox("Current Custom Columns")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(4)

        self._col_rows_layout = QVBoxLayout()
        self._col_rows_layout.setSpacing(4)
        grp_layout.addLayout(self._col_rows_layout)
        root.addWidget(grp)

        self._refresh_col_rows()

        # ── Add new column ─────────────────────────────────────
        add_grp = QGroupBox("Add New Column")
        add_layout = QHBoxLayout(add_grp)
        add_layout.setSpacing(8)

        add_layout.addWidget(QLabel("Name:"))
        self.txt_col_name = QLineEdit()
        self.txt_col_name.setPlaceholderText("e.g. Color, Grade, Location")
        self.txt_col_name.setMinimumHeight(32)
        add_layout.addWidget(self.txt_col_name, stretch=2)

        add_layout.addWidget(QLabel("Type:"))
        self.cmb_col_type = QComboBox()
        self.cmb_col_type.addItems(["Text", "Number"])
        self.cmb_col_type.setMinimumHeight(32)
        self.cmb_col_type.setMinimumWidth(90)
        add_layout.addWidget(self.cmb_col_type)

        btn_add = QPushButton("+ Add")
        btn_add.setStyleSheet(
            "background:#27ae60; color:white; border-radius:4px; padding:6px 16px;"
        )
        btn_add.clicked.connect(self._add_column)
        add_layout.addWidget(btn_add)

        root.addWidget(add_grp)
        root.addStretch()

        # ── Dialog buttons ─────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _refresh_col_rows(self):
        # Clear existing widgets
        while self._col_rows_layout.count():
            item = self._col_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._columns:
            lbl = QLabel("No custom columns yet.")
            lbl.setStyleSheet("color:#888; padding:4px;")
            self._col_rows_layout.addWidget(lbl)
            return

        for i, col in enumerate(self._columns):
            row = QHBoxLayout()
            lbl_name = QLabel(col["name"])
            lbl_name.setMinimumWidth(160)
            lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_type = QLabel(col["type"].upper())
            lbl_type.setStyleSheet(
                "color:white; background:#2980b9; border-radius:3px;"
                " padding:2px 8px; font-size:10px;"
                if col["type"] == "number"
                else
                "color:white; background:#8e44ad; border-radius:3px;"
                " padding:2px 8px; font-size:10px;"
            )
            lbl_type.setFixedWidth(70)
            lbl_type.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_del = QPushButton("✕ Remove")
            btn_del.setStyleSheet(
                "background:#e74c3c; color:white; border-radius:3px; padding:4px 10px;"
            )
            btn_del.setFixedWidth(90)
            btn_del.clicked.connect(lambda _, idx=i: self._remove_column(idx))

            row.addWidget(lbl_name)
            row.addWidget(lbl_type)
            row.addStretch()
            row.addWidget(btn_del)

            wrapper = QWidget()
            wrapper.setLayout(row)
            wrapper.setStyleSheet(
                "background:#f8f9fa; border:1px solid #e0e0e0; border-radius:4px;"
            )
            self._col_rows_layout.addWidget(wrapper)

    def _add_column(self):
        name = self.txt_col_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Column name cannot be empty.")
            return
        # Prevent duplicate names
        existing = [c["name"].lower() for c in self._columns]
        if name.lower() in existing:
            QMessageBox.warning(self, "Duplicate", f'Column "{name}" already exists.')
            return
        self._columns.append({
            "name": name,
            "type": self.cmb_col_type.currentText().lower()
        })
        self.txt_col_name.clear()
        self._refresh_col_rows()

    def _remove_column(self, idx: int):
        col_name = self._columns[idx]["name"]
        reply = QMessageBox.question(
            self, "Remove Column",
            f'Remove column "{col_name}"?\n'
            f'Existing data in this column will be hidden but not deleted.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._columns.pop(idx)
            self._refresh_col_rows()

    def _save(self):
        AppConfig.save_custom_stock_columns(self._columns)
        self.accept()


# ── Stock Add/Edit Dialog ─────────────────────────────────────
class StockDialog(QDialog):
    def __init__(self, parent=None, item: dict = None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit Item" if item else "Add Stock Item")
        self.setMinimumWidth(480)
        self._custom_cols = AppConfig.custom_stock_columns()
        self._custom_inputs = {}   # col_name → widget
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
        _comp.activated.connect(self._on_catalog_selected)

        self.cmb_cat   = QComboBox(); self.cmb_cat.addItems(AppConfig.categories()); self.cmb_cat.setMinimumHeight(32)
        self.cmb_pur   = QComboBox(); self.cmb_pur.addItems(PURITIES); self.cmb_pur.setMinimumHeight(32)
        self.spn_gross = dspin(); self.spn_gross.setSuffix(" g")
        self.spn_net   = dspin(); self.spn_net.setSuffix(" g")
        self.spn_qty   = ispin()
        self.spn_buy   = dspin(); self.spn_buy.setPrefix("₹ ")
        self.spn_sell  = dspin(); self.spn_sell.setPrefix("₹ ")
        self.cmb_vend  = QComboBox(); self.cmb_vend.setMinimumHeight(32)
        self.txt_rem   = le("Optional remarks")

        vendors = get_all_vendors()
        self.cmb_vend.addItem("-- None --", "")
        for v in vendors:
            self.cmb_vend.addItem(v.get("vendor_name", ""), v.get("vendor_id", ""))

        form.addRow("Item Name *",  self.txt_name)
        form.addRow("Category",     self.cmb_cat)
        form.addRow("Purity",       self.cmb_pur)
        form.addRow("Gross Weight", self.spn_gross)
        form.addRow("Net Weight",   self.spn_net)
        form.addRow("Quantity",     self.spn_qty)
        form.addRow("Buy Price",    self.spn_buy)
        form.addRow("Sell Price",   self.spn_sell)
        form.addRow("Vendor",       self.cmb_vend)
        form.addRow("Remarks",      self.txt_rem)

        # ── Dynamic custom columns ─────────────────────────────
        if self._custom_cols:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color:#ddd;")
            form.addRow(sep)
            lbl_custom = QLabel("Custom Fields")
            lbl_custom.setStyleSheet("color:#7f8c8d; font-size:11px;")
            form.addRow(lbl_custom)

            for col in self._custom_cols:
                if col["type"] == "number":
                    widget = QDoubleSpinBox()
                    widget.setRange(-9999999, 9999999)
                    widget.setDecimals(3)
                    widget.setMinimumHeight(32)
                else:
                    widget = QLineEdit()
                    widget.setPlaceholderText(f"Enter {col['name']}")
                    widget.setMinimumHeight(32)

                self._custom_inputs[col["name"]] = widget
                type_badge = f"  [{col['type'].upper()}]"
                form.addRow(col["name"] + type_badge, widget)

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
        self.txt_name.setText(item.get("item_name", ""))
        idx = self.cmb_cat.findText(item.get("category", ""))
        if idx >= 0: self.cmb_cat.setCurrentIndex(idx)
        idx = self.cmb_pur.findText(item.get("purity", ""))
        if idx >= 0: self.cmb_pur.setCurrentIndex(idx)
        self.spn_gross.setValue(item.get("gross_weight", 0))
        self.spn_net.setValue(item.get("net_weight", 0))
        self.spn_qty.setValue(item.get("quantity", 0))
        self.spn_buy.setValue(item.get("purchase_price", 0))
        self.spn_sell.setValue(item.get("selling_price", 0))
        self.txt_rem.setText(item.get("remarks", ""))

        # Populate custom fields
        custom_data = item.get("custom_fields", {})
        for col_name, widget in self._custom_inputs.items():
            val = custom_data.get(col_name, "")
            if isinstance(widget, QDoubleSpinBox):
                try:
                    widget.setValue(float(val) if val != "" else 0.0)
                except (ValueError, TypeError):
                    widget.setValue(0.0)
            else:
                widget.setText(str(val) if val else "")

    def _save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Item name is required.")
            return

        # Collect custom field values
        custom_fields = {}
        for col_name, widget in self._custom_inputs.items():
            if isinstance(widget, QDoubleSpinBox):
                custom_fields[col_name] = widget.value()
            else:
                custom_fields[col_name] = widget.text().strip()

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
            "custom_fields":  custom_fields,
        }
        ensure_item_exists(self.result_data["item_name"], self.result_data["category"])
        self.accept()


# ── Stock Page ────────────────────────────────────────────────
class StockPage(QWidget):
    def __init__(self):
        super().__init__()
        self._all_stock: list[dict] = []
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
        self._root = QVBoxLayout(container)
        self._root.setContentsMargins(25, 20, 25, 20)
        self._root.setSpacing(14)

        # ── Title + buttons ────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel("📦  Stock Management")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))

        btn_add = QPushButton("➕  Add Item")
        btn_add.setStyleSheet("background:#27ae60; color:white; border-radius:4px; padding:8px 16px;")
        btn_add.clicked.connect(self._add)

        btn_cols = QPushButton("⚙  Manage Columns")
        btn_cols.setStyleSheet("background:#8e44ad; color:white; border-radius:4px; padding:8px 16px;")
        btn_cols.clicked.connect(self._manage_columns)

        top.addWidget(title)
        top.addStretch()
        top.addWidget(btn_cols)
        top.addWidget(btn_add)
        self._root.addLayout(top)

        # ── Search ─────────────────────────────────────────────
        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by name, category or vendor...")
        self.txt_search.setMinimumHeight(34)
        self.txt_search.textChanged.connect(self._do_search)
        search_row.addWidget(QLabel("🔍"))
        search_row.addWidget(self.txt_search)
        self._root.addLayout(search_row)

        # ── Table ──────────────────────────────────────────────
        self.tbl = QTableWidget()
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(380)
        # Double-click a row → open edit dialog
        self.tbl.itemDoubleClicked.connect(lambda _: self._edit())
        # Right-click context menu
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._show_context_menu)
        self._root.addWidget(self.tbl)

        # hint label
        hint = QLabel("Tip: Double-click a row to edit  |  Right-click for options")
        hint.setStyleSheet("color:#999; font-size:11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._root.addWidget(hint)

        # ── Action buttons ─────────────────────────────────────
        act = QHBoxLayout(); act.addStretch()
        btn_edit = QPushButton("✏️  Edit Selected")
        btn_edit.setStyleSheet("background:#2980b9; color:white; border-radius:4px; padding:8px 16px;")
        btn_edit.clicked.connect(self._edit)
        btn_del = QPushButton("🗑  Delete Selected")
        btn_del.setStyleSheet("background:#e74c3c; color:white; border-radius:4px; padding:8px 16px;")
        btn_del.clicked.connect(self._delete)
        act.addWidget(btn_edit); act.addWidget(btn_del)
        self._root.addLayout(act)

    def _setup_table_columns(self):
        """Build table headers: fixed cols + custom cols."""
        custom_cols = AppConfig.custom_stock_columns()
        fixed_headers = [
            "ID", "Item Name", "Category", "Purity",
            "Gross(g)", "Net(g)", "Qty", "Buy Price", "Sell Price", "Vendor"
        ]
        custom_headers = [c['name'] for c in custom_cols]
        all_headers = fixed_headers + custom_headers
        self.tbl.setColumnCount(len(all_headers))
        self.tbl.setHorizontalHeaderLabels(all_headers)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnHidden(0, True)

    def refresh(self):
        self._all_stock = get_all_stock()
        self._setup_table_columns()
        self._populate(self._all_stock)

    def _do_search(self, text: str):
        q = text.lower()
        filtered = [s for s in self._all_stock if
                    q in s.get("item_name", "").lower() or
                    q in s.get("category", "").lower() or
                    q in s.get("vendor_name", "").lower()]
        self._populate(filtered)

    def _populate(self, data: list):
        custom_cols = AppConfig.custom_stock_columns()
        self.tbl.setRowCount(0)

        for item in data:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)

            fixed_vals = [
                item.get("item_id",       ""),
                item.get("item_name",     ""),
                item.get("category",      ""),
                item.get("purity",        ""),
                str(item.get("gross_weight", "")),
                str(item.get("net_weight",   "")),
                str(item.get("quantity",     "")),
                format_currency(item.get("purchase_price", 0)),
                format_currency(item.get("selling_price",  0)),
                item.get("vendor_name",   ""),
            ]

            # Custom field values
            custom_data = item.get("custom_fields", {})
            custom_vals = [str(custom_data.get(c["name"], "")) for c in custom_cols]

            for c, v in enumerate(fixed_vals + custom_vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Highlight low-qty in red
                if c == 6 and item.get("quantity", 1) <= 2:
                    cell.setForeground(Qt.GlobalColor.red)
                # Tint custom column cells lightly
                if c >= FIXED_COLS:
                    cell.setBackground(Qt.GlobalColor.white)
                self.tbl.setItem(r, c, cell)

        self.tbl.setColumnHidden(0, True)

    def _show_context_menu(self, pos: QPoint):
        row = self.tbl.rowAt(pos.y())
        if row < 0:
            return
        self.tbl.selectRow(row)
        menu = QMenu(self)
        act_edit = QAction("✏️  Edit", self)
        act_edit.triggered.connect(self._edit)
        act_del  = QAction("🗑  Delete", self)
        act_del.triggered.connect(self._delete)
        menu.addAction(act_edit)
        menu.addSeparator()
        menu.addAction(act_del)
        menu.exec(self.tbl.viewport().mapToGlobal(pos))

    def _manage_columns(self):
        dlg = ManageColumnsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Reload table with updated columns
            self.refresh()

    def _add(self):
        dlg = StockDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            s = StockModel(**{
                k: v for k, v in dlg.result_data.items()
                if k in StockModel.__dataclass_fields__
            })
            d = s.to_dict()
            d["custom_fields"] = dlg.result_data.get("custom_fields", {})
            from app.utils import unique_id
            d["item_id"] = unique_id()
            from services.stock_service import get_all_stock, save_all_stock
            stock = get_all_stock()
            stock.append(d)
            save_all_stock(stock)
            self.refresh()

    def _edit(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Edit", "Select a row first.")
            return
        item_id = self.tbl.item(row, 0).text()
        item = next((s for s in self._all_stock if s.get("item_id") == item_id), None)
        if not item:
            return
        dlg = StockDialog(self, item=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            update_item(item_id, dlg.result_data)
            self.refresh()

    def _delete(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.information(self, "Delete", "Select a row first.")
            return
        item_id = self.tbl.item(row, 0).text()
        name    = self.tbl.item(row, 1).text()
        reply = QMessageBox.question(
            self, "Delete", f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_item(item_id)
            self.refresh()
