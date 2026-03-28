# ============================================================
# ui/invoice_page.py - Invoice / Billing Page (Jewelry Format)
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QFrame, QScrollArea, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from app.config import AppConfig
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf
from services.invoice_service import create_invoice


PURITY_OPTIONS = ["22Kt", "18Kt", "14Kt", "92.5", "99.9", "60-70", "Other"]


class InvoicePage(QWidget):
    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._last_invoice: dict = {}
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
        root.setSpacing(16)

        # Title bar
        top = QHBoxLayout()
        title = QLabel("🧾  New Invoice")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self._inv_num_lbl = QLabel()
        self._inv_num_lbl.setStyleSheet("color: #f39c12; font-size: 14px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self._inv_num_lbl)
        root.addLayout(top)

        # ── Customer Section ──────────────────────────────────
        cust_grp = QGroupBox("Customer Details")
        cf = QFormLayout(cust_grp)
        cf.setSpacing(8)
        cf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_cname    = QLineEdit(); self.txt_cname.setPlaceholderText("Customer name *")
        self.txt_cmobile  = QLineEdit(); self.txt_cmobile.setPlaceholderText("Mobile number")
        self.txt_cemail   = QLineEdit(); self.txt_cemail.setPlaceholderText("Email address")
        self.txt_caddr    = QLineEdit(); self.txt_caddr.setPlaceholderText("Address")
        self.txt_cust_gst = QLineEdit(); self.txt_cust_gst.setPlaceholderText("Customer GST No. (optional)")

        for w in (self.txt_cname, self.txt_cmobile, self.txt_cemail, self.txt_caddr, self.txt_cust_gst):
            w.setMinimumHeight(34)

        cf.addRow("Name *",       self.txt_cname)
        cf.addRow("Mobile",       self.txt_cmobile)
        cf.addRow("Email",        self.txt_cemail)
        cf.addRow("Address",      self.txt_caddr)
        cf.addRow("Customer GST", self.txt_cust_gst)
        root.addWidget(cust_grp)

        # ── Item Entry Section ────────────────────────────────
        item_grp = QGroupBox("Add Item")
        il = QVBoxLayout(item_grp)
        il.setSpacing(8)

        # Row 1: Name | Category | HSN Code | Purity
        row1 = QHBoxLayout(); row1.setSpacing(8)
        self.txt_iname  = QLineEdit(); self.txt_iname.setPlaceholderText("Item name *")
        self.cmb_cat    = QComboBox()
        self.txt_hsn    = QLineEdit(); self.txt_hsn.setPlaceholderText("HSN"); self.txt_hsn.setText("7113"); self.txt_hsn.setMaximumWidth(80)
        self.cmb_purity = QComboBox(); self.cmb_purity.addItems(PURITY_OPTIONS); self.cmb_purity.setEditable(True); self.cmb_purity.setMaximumWidth(100)

        for w in (self.txt_iname, self.cmb_cat, self.txt_hsn, self.cmb_purity):
            w.setMinimumHeight(34)
        row1.addWidget(QLabel("Item:"));     row1.addWidget(self.txt_iname, 2)
        row1.addWidget(QLabel("Category:")); row1.addWidget(self.cmb_cat)
        row1.addWidget(QLabel("HSN:"));      row1.addWidget(self.txt_hsn)
        row1.addWidget(QLabel("Purity:"));   row1.addWidget(self.cmb_purity)

        # Row 2: Qty | Gross Weight | Less Weight | Rate/g
        row2 = QHBoxLayout(); row2.setSpacing(8)
        self.spn_qty      = QSpinBox();       self.spn_qty.setRange(1, 9999); self.spn_qty.setValue(1)
        self.spn_gross_wt = QDoubleSpinBox(); self.spn_gross_wt.setRange(0, 99999); self.spn_gross_wt.setDecimals(3); self.spn_gross_wt.setSuffix(" g")
        self.spn_less_wt  = QDoubleSpinBox(); self.spn_less_wt.setRange(0, 99999);  self.spn_less_wt.setDecimals(3);  self.spn_less_wt.setSuffix(" g")
        self.spn_rate     = QDoubleSpinBox(); self.spn_rate.setRange(0, 9999999);   self.spn_rate.setDecimals(2);     self.spn_rate.setPrefix("₹ ")
        self.lbl_nett     = QLabel("Nett: 0.000 g")
        self.lbl_nett.setStyleSheet("color:#27ae60; font-weight:bold; font-size:12px;")

        for w in (self.spn_qty, self.spn_gross_wt, self.spn_less_wt, self.spn_rate):
            w.setMinimumHeight(34)

        self.spn_gross_wt.valueChanged.connect(self._update_nett_label)
        self.spn_less_wt.valueChanged.connect(self._update_nett_label)

        row2.addWidget(QLabel("Qty:"));       row2.addWidget(self.spn_qty)
        row2.addWidget(QLabel("Gross Wt:"));  row2.addWidget(self.spn_gross_wt)
        row2.addWidget(QLabel("Less Wt:"));   row2.addWidget(self.spn_less_wt)
        row2.addWidget(self.lbl_nett)
        row2.addWidget(QLabel("Rate/g:"));    row2.addWidget(self.spn_rate)

        # Row 3: Making Charge | Stone Charge | Discount
        row3 = QHBoxLayout(); row3.setSpacing(8)
        self.spn_making = QDoubleSpinBox(); self.spn_making.setRange(0, 9999999); self.spn_making.setDecimals(2); self.spn_making.setPrefix("₹ ")
        self.spn_stone  = QDoubleSpinBox(); self.spn_stone.setRange(0, 9999999);  self.spn_stone.setDecimals(2);  self.spn_stone.setPrefix("₹ ")
        self.spn_disc   = QDoubleSpinBox(); self.spn_disc.setRange(0, 9999999);   self.spn_disc.setDecimals(2);   self.spn_disc.setPrefix("₹ ")

        for w in (self.spn_making, self.spn_stone, self.spn_disc):
            w.setMinimumHeight(34)
        row3.addWidget(QLabel("Making Charge:")); row3.addWidget(self.spn_making)
        row3.addWidget(QLabel("Stone Charge:")); row3.addWidget(self.spn_stone)
        row3.addWidget(QLabel("Discount:"));     row3.addWidget(self.spn_disc)
        row3.addStretch()

        btn_add = QPushButton("➕  Add Item")
        btn_add.setMinimumHeight(38)
        btn_add.setStyleSheet(
            "QPushButton { background:#27ae60; color:white; border-radius:5px; padding:0 16px; }"
            "QPushButton:hover { background:#229954; }"
        )
        btn_add.clicked.connect(self._add_item)

        il.addLayout(row1)
        il.addLayout(row2)
        il.addLayout(row3)
        il.addWidget(btn_add, alignment=Qt.AlignmentFlag.AlignRight)
        root.addWidget(item_grp)

        # ── Items Table ───────────────────────────────────────
        items_grp = QGroupBox("Invoice Items")
        itl = QVBoxLayout(items_grp)

        self.tbl_items = QTableWidget()
        self.tbl_items.setColumnCount(11)
        self.tbl_items.setHorizontalHeaderLabels([
            "#", "Item", "HSN", "Purity", "Qty",
            "Gross Wt", "Less Wt", "Nett Wt",
            "Rate/g", "Making", "Amount"
        ])
        self.tbl_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_items.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.setMinimumHeight(180)

        btn_del = QPushButton("🗑  Remove Selected")
        btn_del.setStyleSheet(
            "QPushButton { background:#e74c3c; color:white; border-radius:4px; padding:6px 14px; }"
            "QPushButton:hover { background:#c0392b; }"
        )
        btn_del.clicked.connect(self._remove_item)

        itl.addWidget(self.tbl_items)
        itl.addWidget(btn_del, alignment=Qt.AlignmentFlag.AlignRight)
        root.addWidget(items_grp)

        # ── Tax + Payment ─────────────────────────────────────
        bottom = QHBoxLayout(); bottom.setSpacing(16)

        # Payment details box
        pay_grp = QGroupBox("Payment Details")
        pfl = QFormLayout(pay_grp)
        pfl.setSpacing(8)
        pfl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spn_cash  = QDoubleSpinBox(); self.spn_cash.setRange(0, 9999999); self.spn_cash.setDecimals(2); self.spn_cash.setPrefix("₹ ")
        self.spn_due   = QDoubleSpinBox(); self.spn_due.setRange(0, 9999999);  self.spn_due.setDecimals(2);  self.spn_due.setPrefix("₹ ")
        self.txt_due_date = QLineEdit();   self.txt_due_date.setPlaceholderText("e.g. 31 Dec 25")

        for w in (self.spn_cash, self.spn_due, self.txt_due_date):
            w.setMinimumHeight(32)

        pfl.addRow("Cash Paid:",  self.spn_cash)
        pfl.addRow("Due Amount:", self.spn_due)
        pfl.addRow("Due Date:",   self.txt_due_date)
        bottom.addWidget(pay_grp)

        # Totals box
        totals_frame = QFrame()
        totals_frame.setStyleSheet(
            "QFrame { background:white; border:1px solid #e0e0e0; border-radius:6px; padding:10px; }"
        )
        tfl = QFormLayout(totals_frame)
        tfl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        tfl.setSpacing(8)

        self.lbl_subtotal = QLabel("₹ 0.00")
        self.spn_cgst = QDoubleSpinBox(); self.spn_cgst.setRange(0, 14); self.spn_cgst.setDecimals(2); self.spn_cgst.setSuffix(" %"); self.spn_cgst.setValue(1.5)
        self.spn_sgst = QDoubleSpinBox(); self.spn_sgst.setRange(0, 14); self.spn_sgst.setDecimals(2); self.spn_sgst.setSuffix(" %"); self.spn_sgst.setValue(1.5)
        self.lbl_cgst_amt = QLabel("₹ 0.00")
        self.lbl_sgst_amt = QLabel("₹ 0.00")
        self.lbl_grand    = QLabel("₹ 0.00")
        self.lbl_grand.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_grand.setStyleSheet("color: #27ae60;")

        for w in (self.spn_cgst, self.spn_sgst):
            w.setMinimumHeight(32)
            w.valueChanged.connect(self._recalc_totals)

        tfl.addRow("Gross Amount:", self.lbl_subtotal)
        tfl.addRow("CGST %:",       self.spn_cgst)
        tfl.addRow("CGST Amount:",  self.lbl_cgst_amt)
        tfl.addRow("SGST %:",       self.spn_sgst)
        tfl.addRow("SGST Amount:",  self.lbl_sgst_amt)
        tfl.addRow("NET PAYABLE:",  self.lbl_grand)
        bottom.addWidget(totals_frame)

        root.addLayout(bottom)

        # Notes
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel("Notes:"))
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Any special notes (optional)")
        self.txt_notes.setMinimumHeight(34)
        notes_row.addWidget(self.txt_notes)
        root.addLayout(notes_row)

        # ── Action Buttons ────────────────────────────────────
        act_row = QHBoxLayout(); act_row.setSpacing(12)

        btn_clear = QPushButton("🔄  New / Clear")
        btn_clear.setStyleSheet(
            "QPushButton { background:#7f8c8d; color:white; border-radius:5px; padding:9px 18px; }"
            "QPushButton:hover { background:#95a5a6; }"
        )
        btn_clear.clicked.connect(self._clear_all)

        btn_save = QPushButton("💾  Save Invoice")
        btn_save.setStyleSheet(
            "QPushButton { background:#2980b9; color:white; border-radius:5px; padding:9px 18px; font-weight:bold; }"
            "QPushButton:hover { background:#2471a3; }"
        )
        btn_save.clicked.connect(self._save_invoice)

        btn_print = QPushButton("🖨  Save & Print PDF")
        btn_print.setStyleSheet(
            "QPushButton { background:#f39c12; color:white; border-radius:5px; padding:9px 18px; font-weight:bold; }"
            "QPushButton:hover { background:#e67e22; }"
        )
        btn_print.clicked.connect(self._save_and_print)

        act_row.addStretch()
        act_row.addWidget(btn_clear)
        act_row.addWidget(btn_save)
        act_row.addWidget(btn_print)
        root.addLayout(act_row)

        self._refresh_inv_number()

    # ── Helpers ───────────────────────────────────────────────
    def _update_nett_label(self):
        nett = round(self.spn_gross_wt.value() - self.spn_less_wt.value(), 3)
        self.lbl_nett.setText(f"Nett: {nett:.3f} g")

    def _refresh_inv_number(self):
        prefix = AppConfig.invoice_prefix()
        last   = AppConfig.last_invoice_number()
        self._inv_num_lbl.setText(f"Next: {prefix}-{last+1:04d}")

    def _add_item(self):
        name = self.txt_iname.text().strip()
        if not name:
            QMessageBox.warning(self, "Add Item", "Item name is required.")
            return

        gross_wt = self.spn_gross_wt.value()
        less_wt  = self.spn_less_wt.value()
        nett_wt  = round(gross_wt - less_wt, 3)
        rate     = self.spn_rate.value()
        making   = self.spn_making.value()
        stone    = self.spn_stone.value()
        disc     = self.spn_disc.value()
        total    = round((rate * nett_wt) + making + stone - disc, 2)

        self._items.append({
            "name":          name,
            "category":      self.cmb_cat.currentText(),
            "hsn_code":      self.txt_hsn.text().strip() or "7113",
            "purity":        self.cmb_purity.currentText(),
            "quantity":      self.spn_qty.value(),
            "weight":        gross_wt,
            "less_weight":   less_wt,
            "nett_weight":   nett_wt,
            "rate":          rate,
            "making_charge": making,
            "stone_charge":  stone,
            "discount":      disc,
            "total":         total,
        })
        self._refresh_table()
        self._recalc_totals()

        # Reset
        self.txt_iname.clear()
        self.spn_qty.setValue(1)
        self.spn_gross_wt.setValue(0)
        self.spn_less_wt.setValue(0)
        self.spn_rate.setValue(0)
        self.spn_making.setValue(0)
        self.spn_stone.setValue(0)
        self.spn_disc.setValue(0)
        self.lbl_nett.setText("Nett: 0.000 g")
        self.txt_iname.setFocus()

    def _refresh_table(self):
        self.tbl_items.setRowCount(0)
        for i, item in enumerate(self._items):
            self.tbl_items.insertRow(i)
            vals = [
                str(i+1),
                item["name"],
                item.get("hsn_code", ""),
                item.get("purity", ""),
                str(item["quantity"]),
                f"{item['weight']:.3f}",
                f"{item.get('less_weight', 0):.3f}",
                f"{item.get('nett_weight', 0):.3f}",
                format_currency(item["rate"]),
                format_currency(item["making_charge"]),
                format_currency(item["total"]),
            ]
            for j, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_items.setItem(i, j, cell)

    def _remove_item(self):
        row = self.tbl_items.currentRow()
        if row < 0:
            QMessageBox.information(self, "Remove", "Select a row to remove.")
            return
        del self._items[row]
        self._refresh_table()
        self._recalc_totals()

    def _recalc_totals(self):
        subtotal = sum(i.get("total", 0) for i in self._items)
        cgst_pct = self.spn_cgst.value()
        sgst_pct = self.spn_sgst.value()
        cgst_amt = round(subtotal * cgst_pct / 100, 2)
        sgst_amt = round(subtotal * sgst_pct / 100, 2)
        grand    = round(subtotal + cgst_amt + sgst_amt, 2)

        self.lbl_subtotal.setText(format_currency(subtotal))
        self.lbl_cgst_amt.setText(format_currency(cgst_amt))
        self.lbl_sgst_amt.setText(format_currency(sgst_amt))
        self.lbl_grand.setText(format_currency(grand))

    def _validate(self) -> bool:
        if not self.txt_cname.text().strip():
            QMessageBox.warning(self, "Validation", "Customer name is required.")
            return False
        if not self._items:
            QMessageBox.warning(self, "Validation", "Add at least one item.")
            return False
        return True

    def _build_invoice_data(self) -> dict:
        subtotal = sum(i.get("total", 0) for i in self._items)
        cgst_pct = self.spn_cgst.value()
        sgst_pct = self.spn_sgst.value()
        cgst_amt = round(subtotal * cgst_pct / 100, 2)
        sgst_amt = round(subtotal * sgst_pct / 100, 2)
        grand    = round(subtotal + cgst_amt + sgst_amt, 2)

        return {
            "customer_name":    self.txt_cname.text().strip(),
            "customer_mobile":  self.txt_cmobile.text().strip(),
            "customer_email":   self.txt_cemail.text().strip(),
            "customer_address": self.txt_caddr.text().strip(),
            "customer_gst":     self.txt_cust_gst.text().strip(),
            "items":            list(self._items),
            "subtotal":         round(subtotal, 2),
            "cgst_percent":     cgst_pct,
            "sgst_percent":     sgst_pct,
            "cgst_amount":      cgst_amt,
            "sgst_amount":      sgst_amt,
            "grand_total":      grand,
            "cash_paid":        self.spn_cash.value(),
            "due_amount":       self.spn_due.value(),
            "due_date":         self.txt_due_date.text().strip(),
            "notes":            self.txt_notes.text().strip(),
            "tax_percent":      cgst_pct + sgst_pct,
            "tax_amount":       cgst_amt + sgst_amt,
        }

    def _save_invoice(self):
        if not self._validate():
            return
        extra = self._build_invoice_data()
        inv = create_invoice(
            extra["customer_name"], extra["customer_mobile"],
            extra["customer_address"], list(self._items),
            extra["tax_percent"], notes=extra.get("notes", ""),
            customer_email=extra.get("customer_email", "")
        )
        inv.update(extra)
        self._last_invoice = inv
        QMessageBox.information(self, "Saved", f"Invoice {inv['invoice_number']} saved!")
        self._clear_all()

    def _save_and_print(self):
        if not self._validate():
            return
        extra = self._build_invoice_data()
        inv = create_invoice(
            extra["customer_name"], extra["customer_mobile"],
            extra["customer_address"], list(self._items),
            extra["tax_percent"], notes=extra.get("notes", ""),
            customer_email=extra.get("customer_email", "")
        )
        inv.update(extra)
        self._last_invoice = inv
        self._clear_all()
        save_invoice_as_pdf(inv, parent=self)

    def _clear_all(self):
        self.txt_cname.clear()
        self.txt_cmobile.clear()
        self.txt_cemail.clear()
        self.txt_caddr.clear()
        self.txt_cust_gst.clear()
        self.txt_notes.clear()
        self.txt_due_date.clear()
        self._items.clear()
        self._refresh_table()
        self.spn_cash.setValue(0)
        self.spn_due.setValue(0)
        self.spn_cgst.setValue(1.5)
        self.spn_sgst.setValue(1.5)
        self._recalc_totals()
        self._refresh_inv_number()

    def refresh(self):
        curr = self.cmb_cat.currentText()
        self.cmb_cat.clear()
        self.cmb_cat.addItems(AppConfig.categories())
        if curr:
            idx = self.cmb_cat.findText(curr)
            if idx >= 0: self.cmb_cat.setCurrentIndex(idx)
        self._refresh_inv_number()