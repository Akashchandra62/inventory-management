# ============================================================
# ui/karigar_page.py — Karigar Entry + Karigar Directory
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QHeaderView, QAbstractItemView, QComboBox,
    QGridLayout, QMessageBox, QDateEdit, QGroupBox, QSplitter,
    QStyledItemDelegate, QSizePolicy,
)
from PyQt5.QtCore import Qt, QDate, QEvent
from PyQt5.QtGui import QFont, QColor

from services.karigar_service import (
    get_all_transactions, add_transaction,
    get_next_memo_no,
)


# ── Shared styles ────────────────────────────────────────────
_SECTION_STYLE = (
    "QGroupBox { font-weight: bold; font-size: 11px; color: #2c3e50; "
    "border: 1px solid #d0d0d0; border-radius: 4px; margin-top: 6px; "
    "padding-top: 8px; } "
    "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
)
_INP = (
    "QLineEdit { min-height: 24px; max-height: 24px; padding: 1px 5px; "
    "border: 1px solid #ccc; border-radius: 3px; font-size: 11px; } "
    "QLineEdit:focus { border-color: #f39c12; }"
)
_CMB = (
    "QComboBox { min-height: 24px; max-height: 24px; padding: 1px 5px; "
    "border: 1px solid #ccc; border-radius: 3px; font-size: 11px; }"
)
_DTE = (
    "QDateEdit { min-height: 24px; max-height: 24px; padding: 1px 5px; "
    "border: 1px solid #ccc; border-radius: 3px; font-size: 11px; }"
)
_RO = "background:#f5f5f5;"


def _inp(ph="", readonly=False):
    e = QLineEdit()
    e.setPlaceholderText(ph)
    e.setStyleSheet(_INP + (_RO if readonly else ""))
    if readonly:
        e.setReadOnly(True)
    return e


def _cmb(*opts):
    c = QComboBox()
    c.addItems(list(opts))
    c.setStyleSheet(_CMB)
    return c


def _dt():
    d = QDateEdit(QDate.currentDate())
    d.setCalendarPopup(True)
    d.setDisplayFormat("dd-MM-yyyy")
    d.setStyleSheet(_DTE)
    return d


def _lbl(text):
    l = QLabel(text)
    l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    l.setStyleSheet("font-size:11px;")
    l.setMaximumWidth(90)
    return l


def _amt(readonly=False):
    e = QLineEdit("0.00")
    e.setAlignment(Qt.AlignRight)
    e.setStyleSheet(_INP + (_RO if readonly else ""))
    if readonly:
        e.setReadOnly(True)
    return e


# ── Enter-key delegate for item table ────────────────────────
# Columns 5 & 6 are CGST/SGST (auto, read-only) — skipped in tab order.
_SKIP_COLS = {5, 6}

class _EnterDelegate(QStyledItemDelegate):
    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._tbl = table

    def eventFilter(self, editor, event):
        if (event.type() == QEvent.KeyPress and
                event.key() in (Qt.Key_Return, Qt.Key_Enter)):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)

            row = self._tbl.currentRow()
            col = self._tbl.currentColumn()
            ncol = col + 1
            # skip read-only columns
            while ncol < self._tbl.columnCount() and ncol in _SKIP_COLS:
                ncol += 1

            if ncol < self._tbl.columnCount():
                # move right within row
                self._tbl.setCurrentCell(row, ncol)
                self._tbl.edit(self._tbl.currentIndex())
            else:
                # last editable cell → add new row
                nrow = self._tbl.rowCount()
                self._tbl.insertRow(nrow)
                for c in range(self._tbl.columnCount()):
                    cell = QTableWidgetItem("")
                    if c in _SKIP_COLS:
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                        cell.setBackground(QColor("#f0f0f0"))
                    self._tbl.setItem(nrow, c, cell)
                self._tbl.setCurrentCell(nrow, 0)
                self._tbl.edit(self._tbl.currentIndex())
            return True
        return super().eventFilter(editor, event)


# ============================================================
#  Page 1 — Karigar Entry Form
# ============================================================
class KarigarPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Constrain form width so it doesn't stretch across full ultrawide screen
        wrapper = QWidget()
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)

        form_w = QWidget()
        form_w.setMaximumWidth(820)
        fl = QVBoxLayout(form_w)
        fl.setContentsMargins(20, 14, 20, 16)
        fl.setSpacing(8)

        wl.addWidget(form_w)
        wl.addStretch()
        scroll.setWidget(wrapper)

        title = QLabel("Karigar / Job Work Entry")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet("color:#2c3e50;")
        fl.addWidget(title)

        self._build_karigar_section(fl)
        self._build_order_section(fl)
        self._build_item_table(fl)
        self._build_summary_payment(fl)

        btn_save = QPushButton("  Save Karigar Entry")
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet(
            "QPushButton { background:#27ae60; color:white; border:none; "
            "border-radius:5px; font-size:12px; font-weight:bold; padding:0 18px; } "
            "QPushButton:hover { background:#2ecc71; }"
        )
        btn_save.clicked.connect(self._save)
        fl.addWidget(btn_save, alignment=Qt.AlignLeft)
        fl.addStretch()

        self._setup_enter_nav()

    # ── Karigar Details ──────────────────────────────────────
    def _build_karigar_section(self, parent):
        grp = QGroupBox("Karigar Details")
        grp.setStyleSheet(_SECTION_STYLE)
        g = QGridLayout(grp)
        g.setSpacing(5); g.setContentsMargins(10, 10, 10, 8)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        self.fld_memo     = _inp(readonly=True)
        self.cmb_type     = _cmb("Karigar", "Vendor", "Job Worker", "Goldsmith", "Other")
        self.fld_salesman = _inp("Salesman")
        self.dt_purchase  = _dt()
        self.fld_mobile   = _inp("Mobile")
        self.fld_name     = _inp("Full name")
        self.fld_address  = _inp("Address")
        self.fld_email    = _inp("Email")
        self.cmb_id_type  = _cmb("Aadhar", "Passport", "Voter ID", "Driving License", "Other")
        self.fld_id_no    = _inp("ID Number")
        self.fld_pan      = _inp("PAN Number")
        self.fld_state    = _inp("State")

        g.addWidget(_lbl("Memo No:"),     0, 0); g.addWidget(self.fld_memo,     0, 1)
        g.addWidget(_lbl("Type:"),        0, 2); g.addWidget(self.cmb_type,     0, 3)
        g.addWidget(_lbl("Salesman:"),    1, 0); g.addWidget(self.fld_salesman, 1, 1)
        g.addWidget(_lbl("Purchase Dt:"), 1, 2); g.addWidget(self.dt_purchase,  1, 3)
        g.addWidget(_lbl("Mobile:"),      2, 0); g.addWidget(self.fld_mobile,   2, 1)
        g.addWidget(_lbl("Name:"),        2, 2); g.addWidget(self.fld_name,     2, 3)
        g.addWidget(_lbl("Address:"),     3, 0); g.addWidget(self.fld_address,  3, 1, 1, 3)
        g.addWidget(_lbl("Email:"),       4, 0); g.addWidget(self.fld_email,    4, 1)
        g.addWidget(_lbl("ID Type:"),     4, 2); g.addWidget(self.cmb_id_type,  4, 3)
        g.addWidget(_lbl("ID No:"),       5, 0); g.addWidget(self.fld_id_no,    5, 1)
        g.addWidget(_lbl("PAN:"),         5, 2); g.addWidget(self.fld_pan,      5, 3)
        g.addWidget(_lbl("State:"),       6, 0); g.addWidget(self.fld_state,    6, 1)
        parent.addWidget(grp)

    # ── Order Details ────────────────────────────────────────
    def _build_order_section(self, parent):
        grp = QGroupBox("Order Details")
        grp.setStyleSheet(_SECTION_STYLE)
        g = QGridLayout(grp)
        g.setSpacing(5); g.setContentsMargins(10, 10, 10, 8)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        self.dt_order     = _dt()
        self.fld_order_no = _inp("Order number")

        g.addWidget(_lbl("Order Date:"), 0, 0); g.addWidget(self.dt_order,     0, 1)
        g.addWidget(_lbl("Order No:"),   0, 2); g.addWidget(self.fld_order_no, 0, 3)
        parent.addWidget(grp)

    # ── Item Table ───────────────────────────────────────────
    def _build_item_table(self, parent):
        grp = QGroupBox("Item Details  (fill a row and press Enter on last cell to add next row)")
        grp.setStyleSheet(_SECTION_STYLE)
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(10, 10, 10, 8); layout.setSpacing(4)

        _COLS = ["Description", "Qty Pcs", "Qty Grm", "Taxable (₹)",
                 "GST %", "CGST (₹)", "SGST (₹)", "Remarks"]
        self.tbl_items = QTableWidget(0, len(_COLS))
        self.tbl_items.setHorizontalHeaderLabels(_COLS)
        self.tbl_items.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.verticalHeader().setDefaultSectionSize(26)
        self.tbl_items.setMinimumHeight(120)
        self.tbl_items.setMaximumHeight(220)
        self.tbl_items.itemChanged.connect(self._item_changed)

        delegate = _EnterDelegate(self.tbl_items)
        self.tbl_items.setItemDelegate(delegate)

        layout.addWidget(self.tbl_items)
        self._add_row()
        parent.addWidget(grp)

    def _add_row(self):
        r = self.tbl_items.rowCount()
        self.tbl_items.insertRow(r)
        for c in range(self.tbl_items.columnCount()):
            cell = QTableWidgetItem("")
            if c in _SKIP_COLS:
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                cell.setBackground(QColor("#f0f0f0"))
            self.tbl_items.setItem(r, c, cell)

    def _item_changed(self, item):
        if item.column() not in (3, 4):
            return
        row = item.row()
        cell5 = self.tbl_items.item(row, 5)
        cell6 = self.tbl_items.item(row, 6)
        if cell5 is None or cell6 is None:
            return
        self.tbl_items.blockSignals(True)
        try:    taxable = float((self.tbl_items.item(row, 3) or QTableWidgetItem("")).text() or 0)
        except: taxable = 0.0
        try:    gst = float((self.tbl_items.item(row, 4) or QTableWidgetItem("")).text() or 0)
        except: gst = 0.0
        half = round(taxable * gst / 200.0, 2)
        cell5.setText(f"{half:.2f}"); cell6.setText(f"{half:.2f}")
        self.tbl_items.blockSignals(False)
        self._recalc()

    # ── Bill Summary + Payment ───────────────────────────────
    def _build_summary_payment(self, parent):
        row = QHBoxLayout(); row.setSpacing(10)

        grp_s = QGroupBox("Bill Summary"); grp_s.setStyleSheet(_SECTION_STYLE)
        gs = QGridLayout(grp_s)
        gs.setSpacing(5); gs.setContentsMargins(10, 10, 10, 8); gs.setColumnStretch(1, 1)

        self.fld_gross   = _amt(readonly=True)
        self.fld_cgst_t  = _amt(readonly=True)
        self.fld_sgst_t  = _amt(readonly=True)
        self.fld_total   = _amt(readonly=True)
        self.fld_dis     = _amt()
        self.fld_advance = _amt()
        self.fld_bill    = _amt(readonly=True)
        self.fld_bill.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.fld_bill.setStyleSheet(self.fld_bill.styleSheet() + "color:#27ae60;")
        self.fld_dis.textChanged.connect(self._recalc)
        self.fld_advance.textChanged.connect(self._recalc)

        def sl(t, bold=False):
            l = QLabel(t); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setStyleSheet("font-size:11px;" + ("font-weight:bold;" if bold else ""))
            return l

        gs.addWidget(sl("Gross Amount:"),           0, 0); gs.addWidget(self.fld_gross,   0, 1)
        gs.addWidget(sl("CGST:"),                   1, 0); gs.addWidget(self.fld_cgst_t,  1, 1)
        gs.addWidget(sl("SGST:"),                   2, 0); gs.addWidget(self.fld_sgst_t,  2, 1)
        gs.addWidget(sl("Total Amount:"),           3, 0); gs.addWidget(self.fld_total,   3, 1)
        gs.addWidget(sl("Dis/Round Off:"),          4, 0); gs.addWidget(self.fld_dis,     4, 1)
        gs.addWidget(sl("Advance Less:"),           5, 0); gs.addWidget(self.fld_advance, 5, 1)
        gs.addWidget(sl("Bill Amount:", bold=True), 6, 0); gs.addWidget(self.fld_bill,   6, 1)
        row.addWidget(grp_s)

        grp_p = QGroupBox("Payment Details"); grp_p.setStyleSheet(_SECTION_STYLE)
        gp = QGridLayout(grp_p)
        gp.setSpacing(5); gp.setContentsMargins(10, 10, 10, 8); gp.setColumnStretch(1, 1)

        self.fld_cash    = _amt()
        self.fld_card    = _amt()
        self.fld_cheque  = _amt()
        self.fld_ch_det  = _inp("Cheque no / bank details")
        self.fld_paid    = _amt()
        self.fld_balance = _amt(readonly=True)
        self.fld_balance.setFont(QFont("Segoe UI", 10, QFont.Bold))
        for f in (self.fld_cash, self.fld_card, self.fld_cheque, self.fld_paid):
            f.textChanged.connect(self._recalc_payment)

        def pl(t, bold=False):
            l = QLabel(t); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setStyleSheet("font-size:11px;" + ("font-weight:bold;" if bold else ""))
            return l

        gp.addWidget(pl("Cash:"),                      0, 0); gp.addWidget(self.fld_cash,    0, 1)
        gp.addWidget(pl("Card:"),                      1, 0); gp.addWidget(self.fld_card,    1, 1)
        gp.addWidget(pl("Cheque:"),                    2, 0); gp.addWidget(self.fld_cheque,  2, 1)
        gp.addWidget(pl("Ch Details:"),                3, 0); gp.addWidget(self.fld_ch_det,  3, 1)
        gp.addWidget(pl("Paid Amount:"),               4, 0); gp.addWidget(self.fld_paid,    4, 1)
        gp.addWidget(pl("Balance/Refund:", bold=True), 5, 0); gp.addWidget(self.fld_balance, 5, 1)
        row.addWidget(grp_p)
        parent.addLayout(row)

    # ── Enter key nav for form fields ────────────────────────
    def _setup_enter_nav(self):
        # Ordered list of all navigable fields (skipping readonly)
        seq = [
            self.fld_salesman, self.fld_mobile, self.fld_name,
            self.fld_address, self.fld_email, self.fld_id_no,
            self.fld_pan, self.fld_state, self.fld_order_no,
            self.fld_dis, self.fld_advance,
            self.fld_cash, self.fld_card, self.fld_cheque,
            self.fld_ch_det, self.fld_paid,
        ]
        for i, fld in enumerate(seq):
            nxt = seq[(i + 1) % len(seq)]
            fld.returnPressed.connect(nxt.setFocus)

    # ── Recalculation ────────────────────────────────────────
    def _recalc(self):
        gross = cgst = sgst = 0.0
        for r in range(self.tbl_items.rowCount()):
            def _v(c, row=r):
                try: return float((self.tbl_items.item(row, c) or QTableWidgetItem("")).text() or 0)
                except: return 0.0
            gross += _v(3); cgst += _v(5); sgst += _v(6)
        total = gross + cgst + sgst
        try:    dis = float(self.fld_dis.text() or 0)
        except: dis = 0.0
        try:    adv = float(self.fld_advance.text() or 0)
        except: adv = 0.0
        self.fld_gross.setText(f"{gross:.2f}"); self.fld_cgst_t.setText(f"{cgst:.2f}")
        self.fld_sgst_t.setText(f"{sgst:.2f}"); self.fld_total.setText(f"{total:.2f}")
        self.fld_bill.setText(f"{total - dis - adv:.2f}")
        self._recalc_payment()

    def _recalc_payment(self):
        try:    bill = float(self.fld_bill.text() or 0)
        except: bill = 0.0
        try:    paid = float(self.fld_paid.text() or 0)
        except: paid = 0.0
        self.fld_balance.setText(f"{bill - paid:.2f}")

    # ── Save ─────────────────────────────────────────────────
    def _save(self):
        name = self.fld_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Karigar Name is required.")
            return
        items = []
        for r in range(self.tbl_items.rowCount()):
            def _t(c, row=r):
                return (self.tbl_items.item(row, c) or QTableWidgetItem("")).text().strip()
            def _f(c, row=r):
                try: return float(_t(c, row))
                except: return 0.0
            def _i(c, row=r):
                try: return int(_t(c, row))
                except: return 0
            if not _t(0): continue
            items.append({"description": _t(0), "qty_pcs": _i(1), "qty_grm": _f(2),
                          "taxable": _f(3), "gst_percent": _f(4),
                          "cgst": _f(5), "sgst": _f(6), "remarks": _t(7)})

        def _a(fld):
            try: return float(fld.text() or 0)
            except: return 0.0

        tx = {
            "memo_no":        self.fld_memo.text(),
            "type":           self.cmb_type.currentText(),
            "salesman":       self.fld_salesman.text().strip(),
            "purchase_date":  self.dt_purchase.date().toString("yyyy-MM-dd"),
            "mobile":         self.fld_mobile.text().strip(),
            "name":           name,
            "address":        self.fld_address.text().strip(),
            "email":          self.fld_email.text().strip(),
            "id_type":        self.cmb_id_type.currentText(),
            "id_no":          self.fld_id_no.text().strip(),
            "pan":            self.fld_pan.text().strip(),
            "state":          self.fld_state.text().strip(),
            "order_date":     self.dt_order.date().toString("yyyy-MM-dd"),
            "order_no":       self.fld_order_no.text().strip(),
            "items":          items,
            "gross_amount":   _a(self.fld_gross),  "cgst_total":     _a(self.fld_cgst_t),
            "sgst_total":     _a(self.fld_sgst_t), "total_amount":   _a(self.fld_total),
            "discount":       _a(self.fld_dis),    "advance_less":   _a(self.fld_advance),
            "bill_amount":    _a(self.fld_bill),   "cash":           _a(self.fld_cash),
            "card":           _a(self.fld_card),   "cheque":         _a(self.fld_cheque),
            "ch_details":     self.fld_ch_det.text().strip(),
            "paid_amount":    _a(self.fld_paid),   "balance_refund": _a(self.fld_balance),
        }
        add_transaction(tx)
        QMessageBox.information(self, "Saved", f"Entry {tx['memo_no']} saved.")
        self._reset()

    def _reset(self):
        self.fld_memo.setText(get_next_memo_no())
        for fld in (self.fld_name, self.fld_mobile, self.fld_address, self.fld_email,
                    self.fld_salesman, self.fld_id_no, self.fld_pan,
                    self.fld_state, self.fld_order_no, self.fld_ch_det):
            fld.clear()
        self.dt_purchase.setDate(QDate.currentDate())
        self.dt_order.setDate(QDate.currentDate())
        self.cmb_type.setCurrentIndex(0); self.cmb_id_type.setCurrentIndex(0)
        self.tbl_items.setRowCount(0); self._add_row()
        for fld in (self.fld_gross, self.fld_cgst_t, self.fld_sgst_t, self.fld_total,
                    self.fld_dis, self.fld_advance, self.fld_bill,
                    self.fld_cash, self.fld_card, self.fld_cheque,
                    self.fld_paid, self.fld_balance):
            fld.setText("0.00")

    def refresh(self):
        if not self.fld_memo.text():
            self.fld_memo.setText(get_next_memo_no())


# ============================================================
#  Page 2 — Karigar Directory
# ============================================================
class KarigarDirectoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._all_transactions: list = []
        self._all_karigars: list = []
        self._selected_name: str = ""
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        title = QLabel("Karigar Directory")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setStyleSheet("color:#2c3e50;")
        root.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: karigar list ────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 6, 0); ll.setSpacing(8)

        sh = QHBoxLayout(); sh.setSpacing(6)
        sh.addWidget(QLabel("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Name or mobile…")
        self.txt_search.setStyleSheet(_INP)
        self.txt_search.textChanged.connect(self._apply_karigar_filter)
        sh.addWidget(self.txt_search)
        ll.addLayout(sh)

        _KC = ["Name", "Mobile", "Type", "Bills", "Total (₹)"]
        self.tbl_karigars = QTableWidget(0, len(_KC))
        self.tbl_karigars.setHorizontalHeaderLabels(_KC)
        self.tbl_karigars.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_karigars.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_karigars.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_karigars.setAlternatingRowColors(True)
        self.tbl_karigars.verticalHeader().setVisible(False)
        self.tbl_karigars.verticalHeader().setDefaultSectionSize(30)
        self.tbl_karigars.selectionModel().selectionChanged.connect(self._on_karigar_selected)
        ll.addWidget(self.tbl_karigars)
        splitter.addWidget(left)

        # ── Right: transaction history ────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 0, 0, 0); rl.setSpacing(8)

        hist_lbl = QLabel("Transaction History")
        hist_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        hist_lbl.setStyleSheet("color:#2c3e50;")
        rl.addWidget(hist_lbl)

        flt = QHBoxLayout(); flt.setSpacing(8)
        flt.addWidget(QLabel("From:"))
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-12))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        self.dt_from.setStyleSheet(_DTE)
        self.dt_from.dateChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.dt_from)

        flt.addWidget(QLabel("To:"))
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        self.dt_to.setStyleSheet(_DTE)
        self.dt_to.dateChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.dt_to)

        flt.addWidget(QLabel("Type:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["All", "Karigar", "Vendor", "Job Worker", "Goldsmith", "Other"])
        self.cmb_type.setStyleSheet(_CMB)
        self.cmb_type.currentIndexChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.cmb_type)

        flt.addWidget(QLabel("Order No:"))
        self.txt_order = QLineEdit()
        self.txt_order.setPlaceholderText("Filter…")
        self.txt_order.setStyleSheet(_INP)
        self.txt_order.setMaximumWidth(110)
        self.txt_order.textChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.txt_order)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedHeight(26)
        btn_reset.setStyleSheet(
            "QPushButton { background:#7f8c8d; color:white; border:none; "
            "border-radius:3px; font-size:11px; padding:0 10px; } "
            "QPushButton:hover { background:#626567; }"
        )
        btn_reset.clicked.connect(self._reset_filters)
        flt.addWidget(btn_reset)
        flt.addStretch()
        rl.addLayout(flt)

        _TC = ["Memo No", "Date", "Order No", "Items",
               "Gross (₹)", "CGST (₹)", "SGST (₹)",
               "Bill Amt (₹)", "Paid (₹)", "Balance (₹)"]
        self.tbl_tx = QTableWidget(0, len(_TC))
        self.tbl_tx.setHorizontalHeaderLabels(_TC)
        self.tbl_tx.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_tx.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_tx.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_tx.setAlternatingRowColors(True)
        self.tbl_tx.verticalHeader().setVisible(False)
        self.tbl_tx.verticalHeader().setDefaultSectionSize(30)
        rl.addWidget(self.tbl_tx)

        sf = QFrame()
        sf.setStyleSheet("background:white; border:1px solid #e0e0e0; border-radius:4px;")
        sl = QHBoxLayout(sf); sl.setContentsMargins(14, 5, 14, 5); sl.setSpacing(24)
        self.lbl_bills   = QLabel("Bills: 0")
        self.lbl_total   = QLabel("Total Billed: ₹ 0.00")
        self.lbl_paid    = QLabel("Total Paid: ₹ 0.00")
        self.lbl_balance = QLabel("Balance: ₹ 0.00")
        for lbl in (self.lbl_bills, self.lbl_total, self.lbl_paid, self.lbl_balance):
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("background:transparent; color:#2c3e50;")
            sl.addWidget(lbl)
        sl.addStretch()
        rl.addWidget(sf)

        splitter.addWidget(right)
        splitter.setSizes([320, 680])
        root.addWidget(splitter)

    def refresh(self):
        self._all_transactions = get_all_transactions()
        self._build_karigar_table()

    def _build_karigar_table(self):
        agg: dict = {}
        for tx in self._all_transactions:
            name = tx.get("name", "").strip()
            if not name:
                continue
            if name not in agg:
                agg[name] = {"name": name, "mobile": tx.get("mobile", ""),
                             "type": tx.get("type", ""), "bills": 0, "total": 0.0}
            agg[name]["bills"] += 1
            agg[name]["total"] += float(tx.get("bill_amount", 0) or 0)
        self._all_karigars = list(agg.values())
        self._apply_karigar_filter()

    def _apply_karigar_filter(self):
        q = self.txt_search.text().strip().lower()
        data = self._all_karigars
        if q:
            data = [k for k in data
                    if q in k["name"].lower() or q in k["mobile"].lower()]
        self.tbl_karigars.setRowCount(0)
        for k in data:
            r = self.tbl_karigars.rowCount()
            self.tbl_karigars.insertRow(r)
            for c, v in enumerate([k["name"], k["mobile"], k["type"],
                                    str(k["bills"]), f"{k['total']:,.2f}"]):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(
                    Qt.AlignLeft | Qt.AlignVCenter if c == 0 else Qt.AlignCenter)
                self.tbl_karigars.setItem(r, c, cell)

    def _on_karigar_selected(self):
        row = self.tbl_karigars.currentRow()
        if row < 0:
            return
        self._selected_name = self.tbl_karigars.item(row, 0).text()
        self._apply_tx_filter()

    def _apply_tx_filter(self):
        if not self._selected_name:
            return
        d_from  = self.dt_from.date().toString("yyyy-MM-dd")
        d_to    = self.dt_to.date().toString("yyyy-MM-dd")
        type_f  = self.cmb_type.currentText()
        order_q = self.txt_order.text().strip().lower()

        txs = [
            t for t in self._all_transactions
            if t.get("name") == self._selected_name
            and d_from <= t.get("purchase_date", "") <= d_to
            and (type_f == "All" or t.get("type", "") == type_f)
            and (not order_q or order_q in t.get("order_no", "").lower())
        ]

        self.tbl_tx.setRowCount(0)
        t_bill = t_paid = t_bal = 0.0
        for tx in reversed(txs):
            r = self.tbl_tx.rowCount()
            self.tbl_tx.insertRow(r)
            bill = float(tx.get("bill_amount",    0) or 0)
            paid = float(tx.get("paid_amount",    0) or 0)
            bal  = float(tx.get("balance_refund", 0) or 0)
            t_bill += bill; t_paid += paid; t_bal += bal
            for c, v in enumerate([
                tx.get("memo_no", ""), tx.get("purchase_date", ""),
                tx.get("order_no", ""), str(len(tx.get("items", []))),
                f"{tx.get('gross_amount', 0):,.2f}", f"{tx.get('cgst_total', 0):,.2f}",
                f"{tx.get('sgst_total', 0):,.2f}",
                f"{bill:,.2f}", f"{paid:,.2f}", f"{bal:,.2f}",
            ]):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                if c == 9 and bal > 0:
                    cell.setForeground(QColor("#e74c3c"))
                self.tbl_tx.setItem(r, c, cell)

        self.lbl_bills.setText(f"Bills: {len(txs)}")
        self.lbl_total.setText(f"Total Billed: ₹ {t_bill:,.2f}")
        self.lbl_paid.setText(f"Total Paid: ₹ {t_paid:,.2f}")
        self.lbl_balance.setText(f"Balance: ₹ {t_bal:,.2f}")
        color = "#e74c3c" if t_bal > 0 else "#27ae60"
        self.lbl_balance.setStyleSheet(
            f"background:transparent; color:{color}; font-weight:bold;")

    def _reset_filters(self):
        self.dt_from.setDate(QDate.currentDate().addMonths(-12))
        self.dt_to.setDate(QDate.currentDate())
        self.cmb_type.setCurrentIndex(0)
        self.txt_order.clear()
        self._apply_tx_filter()
