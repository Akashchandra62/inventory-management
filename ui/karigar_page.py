# ============================================================
# ui/karigar_page.py — Karigar Entry + Karigar Directory
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QHeaderView, QAbstractItemView, QComboBox,
    QGridLayout, QMessageBox, QDateEdit, QGroupBox, QSplitter,
    QStyledItemDelegate,
)
from PyQt5.QtCore import Qt, QDate, QEvent, QModelIndex
from PyQt5.QtGui import QFont, QColor

from services.karigar_service import (
    get_all_transactions, add_transaction,
    get_next_memo_no,
)

# ── Shared styles ─────────────────────────────────────────────
_SEC = (
    "QGroupBox { font-weight:bold; font-size:11px; color:#2c3e50; "
    "border:1px solid #d0d0d0; border-radius:4px; margin-top:6px; padding-top:8px; } "
    "QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 4px; }"
)
_INP = (
    "QLineEdit { min-height:24px; max-height:24px; padding:1px 5px; "
    "border:1px solid #ccc; border-radius:3px; font-size:11px; } "
    "QLineEdit:focus { border-color:#f39c12; }"
)
_CMB = "QComboBox { min-height:24px; max-height:24px; padding:1px 5px; border:1px solid #ccc; border-radius:3px; font-size:11px; }"
_DTE = "QDateEdit  { min-height:24px; max-height:24px; padding:1px 5px; border:1px solid #ccc; border-radius:3px; font-size:11px; }"
_RO  = "background:#f5f5f5;"

_SKIP = {5, 6}   # CGST / SGST columns — auto-calculated, not editable


def _inp(ph="", ro=False):
    e = QLineEdit(); e.setPlaceholderText(ph)
    e.setStyleSheet(_INP + (_RO if ro else ""))
    if ro: e.setReadOnly(True)
    return e

def _cmb(*opts):
    c = QComboBox(); c.addItems(list(opts)); c.setStyleSheet(_CMB); return c

def _dt():
    d = QDateEdit(QDate.currentDate())
    d.setCalendarPopup(True); d.setDisplayFormat("dd-MM-yyyy"); d.setStyleSheet(_DTE)
    return d

def _lbl(t):
    l = QLabel(t); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    l.setStyleSheet("font-size:11px;"); l.setMaximumWidth(88)
    return l

def _amt(ro=False):
    e = QLineEdit("0.00"); e.setAlignment(Qt.AlignRight)
    e.setStyleSheet(_INP + (_RO if ro else ""))
    if ro: e.setReadOnly(True)
    return e


# ── Custom table: Enter moves RIGHT, wraps to new row ────────
class _ItemTable(QTableWidget):
    def moveCursor(self, action, modifiers):
        if action == QAbstractItemView.MoveNext:
            row = self.currentRow()
            col = self.currentColumn()
            ncol = col + 1
            while ncol < self.columnCount() and ncol in _SKIP:
                ncol += 1
            if ncol < self.columnCount():
                return self.model().index(row, ncol)
            # last editable cell → insert new row, go to col 0
            nrow = row + 1
            if nrow >= self.rowCount():
                self._append_row()
            return self.model().index(nrow, 0)
        return super().moveCursor(action, modifiers)

    def _append_row(self):
        r = self.rowCount()
        self.insertRow(r)
        for c in range(self.columnCount()):
            cell = QTableWidgetItem("")
            if c in _SKIP:
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                cell.setBackground(QColor("#f0f0f0"))
            self.setItem(r, c, cell)


# ── Delegate: Enter commits + moves to next via moveCursor ───
class _EnterDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() in _SKIP:
            return None
        editor = super().createEditor(parent, option, index)
        if editor and hasattr(editor, "setFrame"):
            editor.setFrame(False)   # removes the floating-box border
        return editor

    def eventFilter(self, editor, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QStyledItemDelegate.EditNextItem)
            return True
        return super().eventFilter(editor, event)


# ============================================================
#  Page 1 — Karigar Entry Form  (left) + Recent List (right)
# ============================================================
class KarigarPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Left: form ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        form_w = QWidget()
        fl = QVBoxLayout(form_w)
        fl.setContentsMargins(20, 14, 16, 16)
        fl.setSpacing(8)
        scroll.setWidget(form_w)

        lbl_title = QLabel("Karigar / Job Work Entry")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_title.setStyleSheet("color:#2c3e50;")
        fl.addWidget(lbl_title)

        self._build_karigar_section(fl)
        self._build_order_section(fl)
        self._build_item_table(fl)
        self._build_summary_payment(fl)

        btn_save = QPushButton("  Save Karigar Entry")
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet(
            "QPushButton{background:#27ae60;color:white;border:none;"
            "border-radius:5px;font-size:12px;font-weight:bold;padding:0 18px;}"
            "QPushButton:hover{background:#2ecc71;}"
        )
        btn_save.clicked.connect(self._save)
        fl.addWidget(btn_save, alignment=Qt.AlignLeft)
        fl.addStretch()

        splitter.addWidget(scroll)

        # ── Right: recent entries ────────────────────────────
        right = QWidget()
        right.setStyleSheet("background:#f8f9fa;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 14, 12, 12)
        rl.setSpacing(8)

        rl_title = QLabel("Recent Entries")
        rl_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        rl_title.setStyleSheet("color:#2c3e50;")
        rl.addWidget(rl_title)

        _RC = ["Memo No", "Name", "Date", "Order No", "Bill Amt (₹)"]
        self.tbl_recent = QTableWidget(0, len(_RC))
        self.tbl_recent.setHorizontalHeaderLabels(_RC)
        self.tbl_recent.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_recent.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_recent.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_recent.setAlternatingRowColors(True)
        self.tbl_recent.verticalHeader().setVisible(False)
        self.tbl_recent.verticalHeader().setDefaultSectionSize(28)
        rl.addWidget(self.tbl_recent)

        splitter.addWidget(right)
        splitter.setSizes([680, 320])

        root.addWidget(splitter)
        self._setup_enter_nav()

    # ── Karigar Details ──────────────────────────────────────
    def _build_karigar_section(self, parent):
        grp = QGroupBox("Karigar Details"); grp.setStyleSheet(_SEC)
        g = QGridLayout(grp)
        g.setSpacing(5); g.setContentsMargins(10, 10, 10, 8)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        self.fld_memo    = _inp(ro=True)
        self.cmb_type    = _cmb("Karigar","Vendor","Job Worker","Goldsmith","Other")
        self.fld_sales   = _inp("Salesman")
        self.dt_purchase = _dt()
        self.fld_mobile  = _inp("Mobile")
        self.fld_name    = _inp("Full name")
        self.fld_addr    = _inp("Address")
        self.fld_email   = _inp("Email")
        self.cmb_idtype  = _cmb("Aadhar","Passport","Voter ID","Driving License","Other")
        self.fld_idno    = _inp("ID Number")
        self.fld_pan     = _inp("PAN")
        self.fld_state   = _inp("State")

        rows = [
            (0, "Memo No:",    self.fld_memo,    "Type:",       self.cmb_type),
            (1, "Salesman:",   self.fld_sales,   "Purchase Dt:",self.dt_purchase),
            (2, "Mobile:",     self.fld_mobile,  "Name:",       self.fld_name),
            (4, "Email:",      self.fld_email,   "ID Type:",    self.cmb_idtype),
            (5, "ID No:",      self.fld_idno,    "PAN:",        self.fld_pan),
            (6, "State:",      self.fld_state,   None,          None),
        ]
        for r, l1, w1, l2, w2 in rows:
            g.addWidget(_lbl(l1), r, 0); g.addWidget(w1, r, 1)
            if l2:
                g.addWidget(_lbl(l2), r, 2); g.addWidget(w2, r, 3)
        # Address spans full width
        g.addWidget(_lbl("Address:"), 3, 0); g.addWidget(self.fld_addr, 3, 1, 1, 3)
        parent.addWidget(grp)

    # ── Order Details ────────────────────────────────────────
    def _build_order_section(self, parent):
        grp = QGroupBox("Order Details"); grp.setStyleSheet(_SEC)
        g = QGridLayout(grp)
        g.setSpacing(5); g.setContentsMargins(10, 10, 10, 8)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        self.dt_order    = _dt()
        self.fld_orderno = _inp("Order number")

        g.addWidget(_lbl("Order Date:"), 0, 0); g.addWidget(self.dt_order,    0, 1)
        g.addWidget(_lbl("Order No:"),   0, 2); g.addWidget(self.fld_orderno, 0, 3)
        parent.addWidget(grp)

    # ── Item Table ───────────────────────────────────────────
    def _build_item_table(self, parent):
        grp = QGroupBox("Item Details  —  press Enter to move between cells; "
                        "Enter on last cell adds a new row")
        grp.setStyleSheet(_SEC)
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(10, 10, 10, 8); layout.setSpacing(4)

        _COLS = ["Description", "Qty Pcs", "Qty Grm", "Taxable (₹)",
                 "GST %", "CGST (₹)", "SGST (₹)", "Remarks"]
        self.tbl_items = _ItemTable(0, len(_COLS))
        self.tbl_items.setHorizontalHeaderLabels(_COLS)
        self.tbl_items.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.verticalHeader().setDefaultSectionSize(32)
        self.tbl_items.setMinimumHeight(130)
        self.tbl_items.setMaximumHeight(260)
        self.tbl_items.setItemDelegate(_EnterDelegate(self.tbl_items))
        self.tbl_items.itemChanged.connect(self._item_changed)

        layout.addWidget(self.tbl_items)
        self._append_item_row()
        parent.addWidget(grp)

    def _append_item_row(self):
        self.tbl_items._append_row()

    def _item_changed(self, item):
        if item.column() not in (3, 4):
            return
        row = item.row()
        c5 = self.tbl_items.item(row, 5)
        c6 = self.tbl_items.item(row, 6)
        if c5 is None or c6 is None:
            return
        self.tbl_items.blockSignals(True)
        try:    taxable = float((self.tbl_items.item(row, 3) or QTableWidgetItem("")).text() or 0)
        except: taxable = 0.0
        try:    gst = float((self.tbl_items.item(row, 4) or QTableWidgetItem("")).text() or 0)
        except: gst = 0.0
        half = round(taxable * gst / 200.0, 2)
        c5.setText(f"{half:.2f}"); c6.setText(f"{half:.2f}")
        self.tbl_items.blockSignals(False)
        self._recalc()

    # ── Bill Summary + Payment ───────────────────────────────
    def _build_summary_payment(self, parent):
        row = QHBoxLayout(); row.setSpacing(10)

        grp_s = QGroupBox("Bill Summary"); grp_s.setStyleSheet(_SEC)
        gs = QGridLayout(grp_s)
        gs.setSpacing(5); gs.setContentsMargins(10, 10, 10, 8); gs.setColumnStretch(1, 1)

        self.fld_gross   = _amt(ro=True)
        self.fld_cgst_t  = _amt(ro=True)
        self.fld_sgst_t  = _amt(ro=True)
        self.fld_total   = _amt(ro=True)
        self.fld_dis     = _amt()
        self.fld_advance = _amt()
        self.fld_bill    = _amt(ro=True)
        self.fld_bill.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.fld_bill.setStyleSheet(self.fld_bill.styleSheet() + "color:#27ae60;")
        self.fld_dis.textChanged.connect(self._recalc)
        self.fld_advance.textChanged.connect(self._recalc)

        def sl(t, b=False):
            l = QLabel(t); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setStyleSheet("font-size:11px;" + ("font-weight:bold;" if b else ""))
            return l

        gs.addWidget(sl("Gross Amount:"),      0, 0); gs.addWidget(self.fld_gross,   0, 1)
        gs.addWidget(sl("CGST:"),              1, 0); gs.addWidget(self.fld_cgst_t,  1, 1)
        gs.addWidget(sl("SGST:"),              2, 0); gs.addWidget(self.fld_sgst_t,  2, 1)
        gs.addWidget(sl("Total Amount:"),      3, 0); gs.addWidget(self.fld_total,   3, 1)
        gs.addWidget(sl("Dis/Round Off:"),     4, 0); gs.addWidget(self.fld_dis,     4, 1)
        gs.addWidget(sl("Advance Less:"),      5, 0); gs.addWidget(self.fld_advance, 5, 1)
        gs.addWidget(sl("Bill Amount:", b=True), 6, 0); gs.addWidget(self.fld_bill, 6, 1)
        row.addWidget(grp_s)

        grp_p = QGroupBox("Payment Details"); grp_p.setStyleSheet(_SEC)
        gp = QGridLayout(grp_p)
        gp.setSpacing(5); gp.setContentsMargins(10, 10, 10, 8); gp.setColumnStretch(1, 1)

        self.fld_cash    = _amt()
        self.fld_card    = _amt()
        self.fld_cheque  = _amt()
        self.fld_chdet   = _inp("Cheque no / bank details")
        self.fld_paid    = _amt()
        self.fld_balance = _amt(ro=True)
        self.fld_balance.setFont(QFont("Segoe UI", 10, QFont.Bold))
        for f in (self.fld_cash, self.fld_card, self.fld_cheque, self.fld_paid):
            f.textChanged.connect(self._recalc_payment)

        def pl(t, b=False):
            l = QLabel(t); l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            l.setStyleSheet("font-size:11px;" + ("font-weight:bold;" if b else ""))
            return l

        gp.addWidget(pl("Cash:"),               0, 0); gp.addWidget(self.fld_cash,    0, 1)
        gp.addWidget(pl("Card:"),               1, 0); gp.addWidget(self.fld_card,    1, 1)
        gp.addWidget(pl("Cheque:"),             2, 0); gp.addWidget(self.fld_cheque,  2, 1)
        gp.addWidget(pl("Ch Details:"),         3, 0); gp.addWidget(self.fld_chdet,   3, 1)
        gp.addWidget(pl("Paid Amount:"),        4, 0); gp.addWidget(self.fld_paid,    4, 1)
        gp.addWidget(pl("Balance/Refund:",b=True),5,0); gp.addWidget(self.fld_balance, 5, 1)
        row.addWidget(grp_p)
        parent.addLayout(row)

    # ── Enter navigation for form fields ────────────────────
    def _setup_enter_nav(self):
        seq = [
            self.fld_sales, self.fld_mobile, self.fld_name, self.fld_addr,
            self.fld_email, self.fld_idno, self.fld_pan, self.fld_state,
            self.fld_orderno,
        ]
        for i, f in enumerate(seq[:-1]):
            f.returnPressed.connect(seq[i + 1].setFocus)
        # Last form field → jump into item table first cell
        self.fld_orderno.returnPressed.connect(self._focus_item_table)

    def _focus_item_table(self):
        if self.tbl_items.rowCount() == 0:
            self._append_item_row()
        self.tbl_items.setCurrentCell(0, 0)
        self.tbl_items.setFocus()
        self.tbl_items.edit(self.tbl_items.currentIndex())

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
            items.append({"description":_t(0),"qty_pcs":_i(1),"qty_grm":_f(2),
                          "taxable":_f(3),"gst_percent":_f(4),
                          "cgst":_f(5),"sgst":_f(6),"remarks":_t(7)})

        def _a(fld):
            try: return float(fld.text() or 0)
            except: return 0.0

        tx = {
            "memo_no":       self.fld_memo.text(),
            "type":          self.cmb_type.currentText(),
            "salesman":      self.fld_sales.text().strip(),
            "purchase_date": self.dt_purchase.date().toString("yyyy-MM-dd"),
            "mobile":        self.fld_mobile.text().strip(),
            "name":          name,
            "address":       self.fld_addr.text().strip(),
            "email":         self.fld_email.text().strip(),
            "id_type":       self.cmb_idtype.currentText(),
            "id_no":         self.fld_idno.text().strip(),
            "pan":           self.fld_pan.text().strip(),
            "state":         self.fld_state.text().strip(),
            "order_date":    self.dt_order.date().toString("yyyy-MM-dd"),
            "order_no":      self.fld_orderno.text().strip(),
            "items":         items,
            "gross_amount":  _a(self.fld_gross),  "cgst_total":    _a(self.fld_cgst_t),
            "sgst_total":    _a(self.fld_sgst_t), "total_amount":  _a(self.fld_total),
            "discount":      _a(self.fld_dis),    "advance_less":  _a(self.fld_advance),
            "bill_amount":   _a(self.fld_bill),   "cash":          _a(self.fld_cash),
            "card":          _a(self.fld_card),   "cheque":        _a(self.fld_cheque),
            "ch_details":    self.fld_chdet.text().strip(),
            "paid_amount":   _a(self.fld_paid),   "balance_refund":_a(self.fld_balance),
        }
        add_transaction(tx)
        QMessageBox.information(self, "Saved", f"Entry {tx['memo_no']} saved.")
        self._reset()
        self._reload_recent()

    def _reset(self):
        self.fld_memo.setText(get_next_memo_no())
        for f in (self.fld_name, self.fld_mobile, self.fld_addr, self.fld_email,
                  self.fld_sales, self.fld_idno, self.fld_pan,
                  self.fld_state, self.fld_orderno, self.fld_chdet):
            f.clear()
        self.dt_purchase.setDate(QDate.currentDate())
        self.dt_order.setDate(QDate.currentDate())
        self.cmb_type.setCurrentIndex(0); self.cmb_idtype.setCurrentIndex(0)
        self.tbl_items.setRowCount(0); self._append_item_row()
        for f in (self.fld_gross, self.fld_cgst_t, self.fld_sgst_t, self.fld_total,
                  self.fld_dis, self.fld_advance, self.fld_bill,
                  self.fld_cash, self.fld_card, self.fld_cheque,
                  self.fld_paid, self.fld_balance):
            f.setText("0.00")

    def _reload_recent(self):
        txs = get_all_transactions()
        self.tbl_recent.setRowCount(0)
        for tx in reversed(txs[-30:]):
            r = self.tbl_recent.rowCount()
            self.tbl_recent.insertRow(r)
            for c, v in enumerate([
                tx.get("memo_no", ""), tx.get("name", ""),
                tx.get("purchase_date", ""), tx.get("order_no", ""),
                f"₹ {tx.get('bill_amount', 0):,.2f}",
            ]):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                self.tbl_recent.setItem(r, c, cell)

    def refresh(self):
        if not self.fld_memo.text():
            self.fld_memo.setText(get_next_memo_no())
        self._reload_recent()


# ============================================================
#  Page 2 — Karigar Directory  (vertical, like Customer page)
# ============================================================
class KarigarDirectoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._all_transactions: list = []
        self._all_karigars: list = []
        self._selected_name: str = ""
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
        title = QLabel("Karigar Directory")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        root.addWidget(title)

        # Search
        sr = QHBoxLayout(); sr.setSpacing(8)
        sr.addWidget(QLabel("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Name or mobile…")
        self.txt_search.setMinimumHeight(32)
        self.txt_search.textChanged.connect(self._apply_karigar_filter)
        sr.addWidget(self.txt_search)
        root.addLayout(sr)

        # ── Karigar list ──────────────────────────────────────
        klbl = QLabel("Karigars  —  click a row to view transactions")
        klbl.setStyleSheet("font-weight:bold; color:#555; font-size:11px;")
        root.addWidget(klbl)

        _KC = ["Name", "Mobile", "Type", "Bills", "Total Billed (₹)"]
        self.tbl_karigars = QTableWidget(0, len(_KC))
        self.tbl_karigars.setHorizontalHeaderLabels(_KC)
        self.tbl_karigars.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_karigars.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_karigars.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_karigars.setAlternatingRowColors(True)
        self.tbl_karigars.verticalHeader().setVisible(False)
        self.tbl_karigars.verticalHeader().setDefaultSectionSize(34)
        self.tbl_karigars.setMinimumHeight(200)
        self.tbl_karigars.setMaximumHeight(280)
        self.tbl_karigars.selectionModel().selectionChanged.connect(self._on_karigar_selected)
        root.addWidget(self.tbl_karigars)

        # ── Transaction history ───────────────────────────────
        self.hist_lbl = QLabel("Transaction History")
        self.hist_lbl.setStyleSheet("font-weight:bold; color:#555; font-size:11px;")
        root.addWidget(self.hist_lbl)

        # Filters
        flt = QHBoxLayout(); flt.setSpacing(8)
        flt.addWidget(QLabel("From:"))
        self.dt_from = QDateEdit(QDate.currentDate().addMonths(-12))
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        self.dt_from.setMinimumHeight(30)
        self.dt_from.dateChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.dt_from)

        flt.addWidget(QLabel("To:"))
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        self.dt_to.setMinimumHeight(30)
        self.dt_to.dateChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.dt_to)

        flt.addWidget(QLabel("Type:"))
        self.cmb_type = QComboBox()
        self.cmb_type.setMinimumHeight(30)
        self.cmb_type.addItems(["All","Karigar","Vendor","Job Worker","Goldsmith","Other"])
        self.cmb_type.currentIndexChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.cmb_type)

        flt.addWidget(QLabel("Order No:"))
        self.txt_order = QLineEdit()
        self.txt_order.setPlaceholderText("Filter…")
        self.txt_order.setMinimumHeight(30)
        self.txt_order.setMaximumWidth(120)
        self.txt_order.textChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.txt_order)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedHeight(30)
        btn_reset.setStyleSheet(
            "QPushButton{background:#7f8c8d;color:white;border:none;"
            "border-radius:3px;font-size:11px;padding:0 12px;}"
            "QPushButton:hover{background:#626567;}"
        )
        btn_reset.clicked.connect(self._reset_filters)
        flt.addWidget(btn_reset)
        flt.addStretch()
        root.addLayout(flt)

        # Transaction table
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
        self.tbl_tx.verticalHeader().setDefaultSectionSize(32)
        self.tbl_tx.setMinimumHeight(220)
        root.addWidget(self.tbl_tx)

        # Summary footer
        sf = QFrame()
        sf.setStyleSheet(
            "QFrame{background:white;border:1px solid #e0e0e0;border-radius:5px;padding:4px;}"
        )
        sl = QHBoxLayout(sf); sl.setContentsMargins(14, 6, 14, 6); sl.setSpacing(28)
        self.lbl_bills   = QLabel("Bills: 0")
        self.lbl_total   = QLabel("Total Billed: ₹ 0.00")
        self.lbl_paid    = QLabel("Total Paid: ₹ 0.00")
        self.lbl_balance = QLabel("Balance: ₹ 0.00")
        for lbl in (self.lbl_bills, self.lbl_total, self.lbl_paid, self.lbl_balance):
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("background:transparent; color:#2c3e50;")
            sl.addWidget(lbl)
        sl.addStretch()
        root.addWidget(sf)

    # ── Data ─────────────────────────────────────────────────
    def refresh(self):
        self._all_transactions = get_all_transactions()
        self._build_karigar_table()

    def _build_karigar_table(self):
        agg: dict = {}
        for tx in self._all_transactions:
            name = tx.get("name", "").strip()
            if not name: continue
            if name not in agg:
                agg[name] = {"name": name, "mobile": tx.get("mobile",""),
                             "type": tx.get("type",""), "bills": 0, "total": 0.0}
            agg[name]["bills"] += 1
            agg[name]["total"] += float(tx.get("bill_amount", 0) or 0)
        self._all_karigars = list(agg.values())
        self._apply_karigar_filter()

    def _apply_karigar_filter(self):
        q = self.txt_search.text().strip().lower()
        data = [k for k in self._all_karigars
                if not q or q in k["name"].lower() or q in k["mobile"].lower()]
        self.tbl_karigars.setRowCount(0)
        for k in data:
            r = self.tbl_karigars.rowCount()
            self.tbl_karigars.insertRow(r)
            for c, v in enumerate([k["name"], k["mobile"], k["type"],
                                    str(k["bills"]), f"{k['total']:,.2f}"]):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter if c == 0 else Qt.AlignCenter)
                self.tbl_karigars.setItem(r, c, cell)

    def _on_karigar_selected(self):
        row = self.tbl_karigars.currentRow()
        if row < 0: return
        name = self.tbl_karigars.item(row, 0).text()
        self._selected_name = name
        self.hist_lbl.setText(f"Transaction History  —  {name}")
        self._apply_tx_filter()

    def _apply_tx_filter(self):
        if not self._selected_name: return
        d_from  = self.dt_from.date().toString("yyyy-MM-dd")
        d_to    = self.dt_to.date().toString("yyyy-MM-dd")
        type_f  = self.cmb_type.currentText()
        order_q = self.txt_order.text().strip().lower()

        txs = [t for t in self._all_transactions
               if t.get("name") == self._selected_name
               and d_from <= t.get("purchase_date", "") <= d_to
               and (type_f == "All" or t.get("type","") == type_f)
               and (not order_q or order_q in t.get("order_no","").lower())]

        self.tbl_tx.setRowCount(0)
        t_bill = t_paid = t_bal = 0.0
        for tx in reversed(txs):
            r = self.tbl_tx.rowCount(); self.tbl_tx.insertRow(r)
            bill = float(tx.get("bill_amount",    0) or 0)
            paid = float(tx.get("paid_amount",    0) or 0)
            bal  = float(tx.get("balance_refund", 0) or 0)
            t_bill += bill; t_paid += paid; t_bal += bal
            for c, v in enumerate([
                tx.get("memo_no",""), tx.get("purchase_date",""),
                tx.get("order_no",""), str(len(tx.get("items",[]))),
                f"{tx.get('gross_amount',0):,.2f}", f"{tx.get('cgst_total',0):,.2f}",
                f"{tx.get('sgst_total',0):,.2f}",
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
        self.lbl_balance.setStyleSheet(f"background:transparent;color:{color};font-weight:bold;")

    def _reset_filters(self):
        self.dt_from.setDate(QDate.currentDate().addMonths(-12))
        self.dt_to.setDate(QDate.currentDate())
        self.cmb_type.setCurrentIndex(0)
        self.txt_order.clear()
        self._apply_tx_filter()
