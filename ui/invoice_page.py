# ============================================================
# ui/invoice_page.py - Invoice / Billing Page (Jewelry Format)
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QFrame, QScrollArea, QHeaderView, QAbstractItemView,
    QCompleter, QAbstractSpinBox, QDialog
)
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QDoubleValidator
from app.config import AppConfig
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf
from services.invoice_service import create_invoice
from services.customer_service import get_all_customers
from services.item_catalog_service import get_item_by_code, get_names as get_catalog_names, add_catalog_item
from services.metal_service import get_metals, add_metal as _add_metal_rec


PURITY_OPTIONS = ["22Kt", "18Kt", "14Kt", "92.5", "99.9", "60-70", "Other"]


class InvoicePage(QWidget):
    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._last_invoice: dict = {}
        self._grand_total: float = 0.0
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
        root.setSpacing(16)

        # Title bar
        top = QHBoxLayout()
        title = QLabel("🧾  New Invoice")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self._inv_num_lbl = QLabel()
        self._inv_num_lbl.setStyleSheet("color: #f39c12; font-size: 14px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self._inv_num_lbl)
        root.addLayout(top)

        # ── Customer Section (two rows) ──────────────────────────
        cust_grp = QGroupBox("Customer Details")
        cv = QVBoxLayout(cust_grp)
        cv.setSpacing(5)
        cv.setContentsMargins(10, 8, 10, 8)

        def _lbl(text, w=70):
            l = QLabel(text)
            l.setStyleSheet("color:#555; font-size:11px; font-weight:600;")
            l.setMaximumWidth(w)
            return l

        # Row 1: Mobile | Name | Address | Email | GST
        row1 = QHBoxLayout(); row1.setSpacing(6)
        self.txt_cmobile  = QLineEdit(); self.txt_cmobile.setPlaceholderText("Mobile *")
        self.txt_cname    = QLineEdit(); self.txt_cname.setPlaceholderText("Customer name *")
        self.txt_caddr    = QLineEdit(); self.txt_caddr.setPlaceholderText("Address")
        self.txt_cemail   = QLineEdit(); self.txt_cemail.setPlaceholderText("Email")
        self.txt_cust_gst = QLineEdit(); self.txt_cust_gst.setPlaceholderText("GST No.")
        for w in (self.txt_cmobile, self.txt_cname, self.txt_caddr,
                  self.txt_cemail, self.txt_cust_gst):
            w.setMinimumHeight(32)
        row1.addWidget(_lbl("Mobile *")); row1.addWidget(self.txt_cmobile, 2)
        row1.addWidget(_lbl("Name *"));   row1.addWidget(self.txt_cname, 3)
        row1.addWidget(_lbl("Address"));  row1.addWidget(self.txt_caddr, 3)
        row1.addWidget(_lbl("Email"));    row1.addWidget(self.txt_cemail, 2)
        row1.addWidget(_lbl("GST No.")); row1.addWidget(self.txt_cust_gst, 2)

        # Row 2: Aadhaar | PAN
        row2 = QHBoxLayout(); row2.setSpacing(6)
        self.txt_aadhaar = QLineEdit(); self.txt_aadhaar.setPlaceholderText("Aadhaar No. (12 digits)")
        self.txt_pan     = QLineEdit(); self.txt_pan.setPlaceholderText("PAN No.")
        for w in (self.txt_aadhaar, self.txt_pan):
            w.setMinimumHeight(32)
        self.txt_pan.setMaximumWidth(160)
        row2.addWidget(_lbl("Aadhaar", 60)); row2.addWidget(self.txt_aadhaar, 2)
        row2.addWidget(_lbl("PAN", 36));      row2.addWidget(self.txt_pan)
        row2.addStretch(4)

        cv.addLayout(row1)
        cv.addLayout(row2)

        self._customers_cache: list[dict] = []
        self._setup_customer_autocomplete()
        root.addWidget(cust_grp)

        # ── Invoice Items — inline editable table ────────────────
        # Each row is fully editable. Enter on last field appends a new row.
        items_grp = QGroupBox("Invoice Items")
        items_grp.setStyleSheet(
            "QGroupBox{font-size:11px;color:#7f8c8d;border:1px solid #dfe6e9;"
            "border-radius:6px;margin-top:14px;padding-top:8px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}"
        )
        itl = QVBoxLayout(items_grp)
        itl.setContentsMargins(6, 10, 6, 6)
        itl.setSpacing(4)

        # ── Quick-add toolbar ─────────────────────────────────
        qa_bar = QHBoxLayout()
        qa_bar.addStretch()

        btn_qi = QPushButton("⚡  New Item")
        btn_qi.setToolTip("Quickly add a new item to the catalog (Ctrl+I)")
        btn_qi.setShortcut("Ctrl+I")
        btn_qi.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;border-radius:4px;"
            "padding:4px 12px;font-size:11px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#7d3c98;}"
        )
        btn_qi.clicked.connect(self._quick_add_item)

        btn_qm = QPushButton("⚡  New Metal")
        btn_qm.setToolTip("Quickly add a metal rate (Ctrl+M)")
        btn_qm.setShortcut("Ctrl+M")
        btn_qm.setStyleSheet(
            "QPushButton{background:#16a085;color:white;border-radius:4px;"
            "padding:4px 12px;font-size:11px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#138d75;}"
        )
        btn_qm.clicked.connect(self._quick_add_metal)

        qa_bar.addWidget(btn_qi)
        qa_bar.addWidget(btn_qm)
        itl.addLayout(qa_bar)

        self.tbl_items = QTableWidget()
        self.tbl_items.setColumnCount(14)
        self.tbl_items.setHorizontalHeaderLabels([
            "#", "Tag/RFID", "Item Name", "HUID/Remarks", "Purity", "GWT g", "NWT g",
            "Pcs", "Rate ₹/g", "MK", "MK ₹", "Other ₹", "Total ₹", ""
        ])
        hdr = self.tbl_items.horizontalHeader()
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        # col 0 (#) and col 13 (delete) are truly fixed; all others are Interactive
        # so the user can drag column borders to resize on any screen size.
        _fixed_cols       = {0: 28, 13: 30}
        _interactive_cols = {1: 90, 3: 150, 4: 78, 5: 82, 6: 82,
                             7: 48, 8: 96, 9: 114, 10: 72, 11: 84, 12: 102}
        for col, w in _fixed_cols.items():
            self.tbl_items.setColumnWidth(col, w)
            hdr.setSectionResizeMode(col, QHeaderView.Fixed)
        for col, w in _interactive_cols.items():
            self.tbl_items.setColumnWidth(col, w)
            hdr.setSectionResizeMode(col, QHeaderView.Interactive)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_items.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_items.setAlternatingRowColors(True)
        self.tbl_items.setMinimumHeight(200)
        self.tbl_items.verticalHeader().setDefaultSectionSize(36)

        self._row_widgets: list[dict] = []
        self._append_item_row()   # start with one blank row

        itl.addWidget(self.tbl_items)
        root.addWidget(items_grp)

        # ── Tax + Payment ─────────────────────────────────────
        bottom = QHBoxLayout(); bottom.setSpacing(16)

        # ── Payment Details ───────────────────────────────────
        pay_grp = QGroupBox("Payment Details")
        pfl = QFormLayout(pay_grp)
        pfl.setSpacing(7)
        pfl.setLabelAlignment(Qt.AlignRight)
        pfl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        _num_validator = QDoubleValidator(0.0, 9999999.0, 2)
        _num_validator.setNotation(QDoubleValidator.StandardNotation)

        def _money_edit(placeholder="0.00"):
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            e.setValidator(_num_validator)
            e.setMinimumHeight(32)
            return e

        def _pay_row(amt_edit, detail_edit):
            """₹ label + amount field + detail field in one row."""
            w = QWidget(); w.setStyleSheet("background:transparent;")
            h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4)
            lbl = QLabel("₹"); lbl.setStyleSheet("color:#555;font-weight:600;")
            h.addWidget(lbl)
            h.addWidget(amt_edit, 1)
            h.addWidget(detail_edit, 2)
            return w

        def _single_row(amt_edit):
            """₹ label + amount field."""
            w = QWidget(); w.setStyleSheet("background:transparent;")
            h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(4)
            lbl = QLabel("₹"); lbl.setStyleSheet("color:#555;font-weight:600;")
            h.addWidget(lbl)
            h.addWidget(amt_edit, 1)
            return w

        self.txt_cash = _money_edit()
        pfl.addRow("Cash Paid:", _single_row(self.txt_cash))

        self.txt_card = _money_edit()
        self.txt_card_details = QLineEdit()
        self.txt_card_details.setPlaceholderText("Card / last 4 digits")
        self.txt_card_details.setMinimumHeight(32)
        pfl.addRow("Card:", _pay_row(self.txt_card, self.txt_card_details))

        self.txt_cheque = _money_edit()
        self.txt_cheque_details = QLineEdit()
        self.txt_cheque_details.setPlaceholderText("Cheque no. / bank")
        self.txt_cheque_details.setMinimumHeight(32)
        pfl.addRow("Cheque:", _pay_row(self.txt_cheque, self.txt_cheque_details))

        self.txt_upi = _money_edit()
        pfl.addRow("UPI:", _single_row(self.txt_upi))

        self.txt_due = QLineEdit("0.00")
        self.txt_due.setReadOnly(True)
        self.txt_due.setMinimumHeight(32)
        self.txt_due.setStyleSheet(
            "QLineEdit { background:#fef9e7; color:#e74c3c; font-weight:bold;"
            " border:1px solid #f9ca24; border-radius:4px; padding:4px 8px; }"
        )
        pfl.addRow("Due Amount:", _single_row(self.txt_due))

        self.txt_due_date = QLineEdit()
        self.txt_due_date.setPlaceholderText("e.g. 31 Dec 25")
        self.txt_due_date.setMinimumHeight(32)
        pfl.addRow("Due Date:", self.txt_due_date)

        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Remarks (optional)")
        self.txt_remarks.setMinimumHeight(32)
        pfl.addRow("Remarks:", self.txt_remarks)

        # Auto-recalc due whenever a payment field changes
        for f in (self.txt_cash, self.txt_card, self.txt_cheque, self.txt_upi):
            f.textChanged.connect(self._recalc_due)

        # Enter key navigates through payment fields (like Tab)
        self.txt_cash.returnPressed.connect(lambda: self.txt_card.setFocus())
        self.txt_card.returnPressed.connect(lambda: self.txt_card_details.setFocus())
        self.txt_card_details.returnPressed.connect(lambda: self.txt_cheque.setFocus())
        self.txt_cheque.returnPressed.connect(lambda: self.txt_cheque_details.setFocus())
        self.txt_cheque_details.returnPressed.connect(lambda: self.txt_upi.setFocus())
        self.txt_upi.returnPressed.connect(lambda: self.txt_due_date.setFocus())
        self.txt_due_date.returnPressed.connect(lambda: self.txt_remarks.setFocus())

        bottom.addWidget(pay_grp, 3)

        # ── Totals / Tax ──────────────────────────────────────
        totals_frame = QFrame()
        totals_frame.setStyleSheet(
            "QFrame { background:white; border:1px solid #e0e0e0; border-radius:6px; padding:10px; }"
        )
        tfl = QFormLayout(totals_frame)
        tfl.setLabelAlignment(Qt.AlignRight)
        tfl.setSpacing(8)
        tfl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        def _tax_spn(default=0.0):
            s = QDoubleSpinBox()
            s.setRange(0, 28); s.setDecimals(2); s.setSuffix(" %"); s.setValue(default)
            s.setMinimumHeight(30); s.setMaximumWidth(80)
            s.setButtonSymbols(QAbstractSpinBox.NoButtons)
            return s

        def _amt_lbl(color="#2c3e50"):
            l = QLabel("₹ 0.00")
            l.setStyleSheet(f"color:{color}; font-weight:600; font-size:12px;")
            l.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            return l

        def _tax_row_widget(spn, lbl):
            """Put % spinbox and ₹ amount side-by-side."""
            w = QWidget(); w.setStyleSheet("background:transparent;")
            h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(8)
            h.addWidget(spn)
            h.addWidget(lbl, 1)
            return w

        self.lbl_subtotal = _amt_lbl()

        self.spn_cgst     = _tax_spn(1.5)
        self.lbl_cgst_amt = _amt_lbl("#8e44ad")
        self.spn_sgst     = _tax_spn(1.5)
        self.lbl_sgst_amt = _amt_lbl("#8e44ad")
        self.spn_igst     = _tax_spn(0.0)
        self.lbl_igst_amt = _amt_lbl("#2980b9")

        self.lbl_grand = QLabel("₹ 0.00")
        self.lbl_grand.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_grand.setStyleSheet("color:#27ae60;")
        self.lbl_grand.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        for spn in (self.spn_cgst, self.spn_sgst, self.spn_igst):
            spn.valueChanged.connect(self._recalc_totals)

        tfl.addRow("Gross Amount:", self.lbl_subtotal)
        tfl.addRow("CGST:",  _tax_row_widget(self.spn_cgst, self.lbl_cgst_amt))
        tfl.addRow("SGST:",  _tax_row_widget(self.spn_sgst, self.lbl_sgst_amt))
        tfl.addRow("IGST:",  _tax_row_widget(self.spn_igst, self.lbl_igst_amt))
        tfl.addRow("NET PAYABLE:", self.lbl_grand)

        bottom.addWidget(totals_frame, 2)

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

        btn_print = QPushButton("🖨  Save && Print PDF")
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

    # ── Customer Autocomplete ─────────────────────────────────
    def _setup_customer_autocomplete(self):
        self._customers_cache = get_all_customers()
        mobiles = [c.get("mobile", "") for c in self._customers_cache if c.get("mobile")]
        completer = QCompleter(mobiles, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.txt_cmobile.setCompleter(completer)
        self.txt_cmobile.textChanged.connect(self._autofill_customer)

    def _autofill_customer(self, text: str):
        text = text.strip()
        if len(text) < 6:
            return
        for c in self._customers_cache:
            if c.get("mobile", "") == text:
                # Block signals so autofill doesn't re-trigger this slot
                self.txt_cname.blockSignals(True)
                self.txt_caddr.blockSignals(True)
                self.txt_cemail.blockSignals(True)
                self.txt_cname.setText(c.get("customer_name", ""))
                self.txt_caddr.setText(c.get("address", ""))
                self.txt_cemail.setText(c.get("email", ""))
                self.txt_cname.blockSignals(False)
                self.txt_caddr.blockSignals(False)
                self.txt_cemail.blockSignals(False)
                break

    # ── Inline-table helpers ──────────────────────────────────
    def _append_item_row(self):
        """Append a new editable row; focus its Item Name field."""
        row_idx = self.tbl_items.rowCount()
        self.tbl_items.insertRow(row_idx)
        self.tbl_items.setRowHeight(row_idx, 36)

        lbl_num = QLabel(str(row_idx + 1))
        lbl_num.setAlignment(Qt.AlignCenter)
        lbl_num.setStyleSheet("color:#95a5a6;font-size:11px;background:transparent;")
        self.tbl_items.setCellWidget(row_idx, 0, lbl_num)

        def _dspn(dec=2, max_v=9999999):
            s = QDoubleSpinBox()
            s.setRange(0, max_v); s.setDecimals(dec)
            s.setFrame(False)
            s.setButtonSymbols(QAbstractSpinBox.NoButtons)
            s.setStyleSheet(
                "QDoubleSpinBox{font-size:12px;padding:2px 3px;background:transparent;border:none;}"
                "QDoubleSpinBox:focus{background:#eaf6fd;border:1px solid #3498db;border-radius:3px;}"
            )
            return s

        def _ispn():
            s = QSpinBox()
            s.setRange(1, 9999); s.setValue(1)
            s.setFrame(False)
            s.setButtonSymbols(QAbstractSpinBox.NoButtons)
            s.setStyleSheet(
                "QSpinBox{font-size:12px;padding:2px 3px;background:transparent;border:none;}"
                "QSpinBox:focus{background:#eaf6fd;border:1px solid #3498db;border-radius:3px;}"
            )
            return s

        _field_style = (
            "QLineEdit{font-size:12px;padding:2px 4px;background:transparent;border:none;}"
            "QLineEdit:focus{background:#eaf6fd;border:1px solid #3498db;border-radius:3px;}"
        )

        w_tag = QLineEdit()
        w_tag.setPlaceholderText("Tag / RFID")
        w_tag.setFrame(False)
        w_tag.setStyleSheet(_field_style)

        w_name = QLineEdit()
        w_name.setPlaceholderText("Name / Code *")
        w_name.setFrame(False)
        w_name.setStyleSheet(_field_style)
        # Autocomplete from catalog names
        _cat_names = get_catalog_names()
        if _cat_names:
            _nc = QCompleter(_cat_names, w_name)
            _nc.setCaseSensitivity(Qt.CaseInsensitive)
            _nc.setFilterMode(Qt.MatchContains)
            w_name.setCompleter(_nc)

        w_huid = QLineEdit()
        w_huid.setPlaceholderText("HUID / Remark")
        w_huid.setFrame(False)
        w_huid.setStyleSheet(_field_style)

        w_purity = QComboBox()
        w_purity.addItems(PURITY_OPTIONS)
        w_purity.setEditable(True)
        w_purity.setFrame(False)
        w_purity.setStyleSheet(
            "QComboBox{font-size:11px;padding:1px;background:transparent;border:none;}"
            "QComboBox:focus{background:#eaf6fd;border:1px solid #3498db;border-radius:3px;}"
            "QComboBox::drop-down{border:none;}"
        )

        w_gwt   = _dspn(dec=3)
        w_nwt   = _dspn(dec=3)
        w_qty   = _ispn()
        w_rate  = _dspn(dec=2)
        w_other = _dspn(dec=2)

        # MK cell: small toggle + spinbox
        mk_is_pct = [True]
        mk_wrap = QWidget(); mk_wrap.setStyleSheet("background:transparent;")
        mk_hl = QHBoxLayout(mk_wrap)
        mk_hl.setContentsMargins(2, 1, 2, 1); mk_hl.setSpacing(2)

        w_mk_btn = QPushButton("%")
        w_mk_btn.setFixedSize(24, 26)
        w_mk_btn.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;border-radius:3px;"
            "font-weight:bold;font-size:10px;border:none;}"
            "QPushButton:hover{background:#7d3c98;}"
        )
        w_mk_spn = _dspn(dec=2)
        w_mk_spn.setSuffix(" %"); w_mk_spn.setRange(0, 100)
        mk_hl.addWidget(w_mk_btn); mk_hl.addWidget(w_mk_spn, 1)

        def _rlbl(color):
            l = QLabel("0.00")
            l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet(
                f"color:{color};font-size:11px;font-weight:600;background:transparent;"
            )
            return l

        w_mk_lbl    = _rlbl("#8e44ad")
        w_total_lbl = _rlbl("#27ae60")
        w_total_lbl.setStyleSheet(
            "color:#27ae60;font-size:12px;font-weight:bold;"
            "background:#eafaf1;border-radius:3px;border:none;"
        )

        w_del = QPushButton("✕")
        w_del.setFixedSize(26, 26)
        w_del.setStyleSheet(
            "QPushButton{background:#fdecea;color:#e74c3c;border:none;"
            "border-radius:3px;font-weight:bold;font-size:11px;}"
            "QPushButton:hover{background:#e74c3c;color:white;}"
        )

        for col, widget in enumerate([
            lbl_num, w_tag, w_name, w_huid, w_purity, w_gwt, w_nwt,
            w_qty, w_rate, mk_wrap, w_mk_lbl, w_other, w_total_lbl, w_del
        ]):
            self.tbl_items.setCellWidget(row_idx, col, widget)

        rd = {
            'tag': w_tag, 'name': w_name, 'huid': w_huid,
            'purity': w_purity,
            'gwt': w_gwt,   'nwt': w_nwt,
            'qty': w_qty,   'rate': w_rate,
            'mk_btn': w_mk_btn, 'mk_spn': w_mk_spn,
            'mk_lbl': w_mk_lbl, 'mk_is_pct': mk_is_pct,
            'other': w_other, 'total_lbl': w_total_lbl,
        }
        self._row_widgets.append(rd)

        # Enter-key chain: tag→name→huid→purity→gwt→nwt→qty→rate→mk_spn→other→(new row)
        chain = [w_tag, w_name, w_huid, w_purity, w_gwt, w_nwt, w_qty, w_rate, w_mk_spn, w_other]
        rd['chain'] = chain
        for ci, w in enumerate(chain):
            if not isinstance(w, QLineEdit):
                w._item_rd   = rd
                w._chain_idx = ci
                w.installEventFilter(self)
        w_tag.returnPressed.connect(lambda _rd=rd: self._focus_and_select(_rd['name']))
        w_name.returnPressed.connect(lambda _rd=rd: self._name_code_lookup(_rd))
        w_huid.returnPressed.connect(lambda _rd=rd: self._focus_and_select(_rd['purity']))

        # GWT → auto-sync NWT
        def _gwt_chg(v, _rd=rd):
            _rd['nwt'].blockSignals(True)
            _rd['nwt'].setValue(v)
            _rd['nwt'].blockSignals(False)
            self._row_calc(_rd)
            self._rebuild_items_from_table()
        w_gwt.valueChanged.connect(_gwt_chg)

        def _any_chg(*_, _rd=rd):
            self._row_calc(_rd)
            self._rebuild_items_from_table()
        for w in (w_nwt, w_qty, w_rate, w_mk_spn, w_other):
            w.valueChanged.connect(_any_chg)

        # MK mode toggle per row
        def _mk_toggle(checked=False, _rd=rd, _mkp=mk_is_pct):
            _mkp[0] = not _mkp[0]
            if _mkp[0]:
                _rd['mk_btn'].setText('%')
                _rd['mk_btn'].setStyleSheet(
                    "QPushButton{background:#8e44ad;color:white;border-radius:3px;"
                    "font-weight:bold;font-size:10px;border:none;}"
                    "QPushButton:hover{background:#7d3c98;}"
                )
                _rd['mk_spn'].setSuffix(' %'); _rd['mk_spn'].setPrefix('')
                _rd['mk_spn'].setRange(0, 100)
            else:
                _rd['mk_btn'].setText('₹')
                _rd['mk_btn'].setStyleSheet(
                    "QPushButton{background:#d35400;color:white;border-radius:3px;"
                    "font-weight:bold;font-size:10px;border:none;}"
                    "QPushButton:hover{background:#b7490a;}"
                )
                _rd['mk_spn'].setSuffix(''); _rd['mk_spn'].setPrefix('₹')
                _rd['mk_spn'].setRange(0, 9999999)
            self._row_calc(_rd)
            self._rebuild_items_from_table()
        w_mk_btn.clicked.connect(_mk_toggle)

        w_del.clicked.connect(lambda _, _rd=rd: self._delete_item_row(_rd))

        QTimer.singleShot(0, w_name.setFocus)

    def _row_calc(self, rd: dict):
        """Recompute MK amount and row total; update display labels."""
        nwt   = rd['nwt'].value()
        rate  = rd['rate'].value()
        metal = nwt * rate
        mk_v  = rd['mk_spn'].value()
        mk_a  = round(metal * mk_v / 100, 2) if rd['mk_is_pct'][0] else mk_v
        other = rd['other'].value()
        total = round(metal + mk_a + other, 2)
        rd['mk_lbl'].setText(f"₹{mk_a:,.2f}")
        rd['total_lbl'].setText(f"₹{total:,.2f}")

    def _rebuild_items_from_table(self):
        """Sync self._items from current widget values then refresh invoice totals."""
        self._items.clear()
        for rd in self._row_widgets:
            name = rd['name'].text().strip()
            if not name:
                continue
            gwt  = rd['gwt'].value()
            nwt  = round(rd['nwt'].value(), 3)
            rate = rd['rate'].value()
            mk_v = rd['mk_spn'].value()
            mk_a = round(nwt * rate * mk_v / 100, 2) if rd['mk_is_pct'][0] else mk_v
            other = rd['other'].value()
            self._items.append({
                'tag':           rd['tag'].text().strip(),
                'name':          name,
                'huid':          rd['huid'].text().strip(),
                'category':      '',
                'hsn_code':      '7113',
                'purity':        rd['purity'].currentText(),
                'quantity':      rd['qty'].value(),
                'weight':        gwt,
                'less_weight':   round(gwt - nwt, 3),
                'nett_weight':   nwt,
                'rate':          rate,
                'making_charge': mk_a,
                'making_pct':    mk_v if rd['mk_is_pct'][0] else 0,
                'stone_charge':  other,
                'discount':      0,
                'total':         round(nwt * rate + mk_a + other, 2),
            })
        self._recalc_totals()

    def _delete_item_row(self, rd: dict):
        """Delete the given row; if it's the only row, just clear it instead."""
        if len(self._row_widgets) <= 1:
            rd['tag'].clear()
            rd['name'].clear()
            rd['huid'].clear()
            for spn in (rd['gwt'], rd['nwt'], rd['rate'], rd['mk_spn'], rd['other']):
                spn.setValue(0)
            rd['qty'].setValue(1)
            rd['mk_lbl'].setText('0.00')
            rd['total_lbl'].setText('0.00')
            self._rebuild_items_from_table()
            return
        idx = self._row_widgets.index(rd)
        self._row_widgets.pop(idx)
        self.tbl_items.removeRow(idx)
        for i in range(len(self._row_widgets)):
            lbl = self.tbl_items.cellWidget(i, 0)
            if lbl: lbl.setText(str(i + 1))
        self._rebuild_items_from_table()

    def _reset_items_table(self):
        """Clear all rows and start fresh with a single empty row."""
        self.tbl_items.setRowCount(0)
        self._row_widgets.clear()
        self._items.clear()
        self._append_item_row()

    def _focus_and_select(self, widget):
        """Focus a widget and select all its text for fast overwrite."""
        widget.setFocus()
        if hasattr(widget, 'selectAll'):
            widget.selectAll()

    def _name_code_lookup(self, rd: dict):
        """On Enter in item name: check if text is a catalog code → auto-fill."""
        text = rd['name'].text().strip()
        if text:
            item = get_item_by_code(text)
            if item:
                # Replace code with actual item name
                rd['name'].blockSignals(True)
                rd['name'].setText(item.get('name', text))
                rd['name'].blockSignals(False)
                # Set purity
                purity = item.get('purity', '')
                if purity:
                    idx = rd['purity'].findText(purity)
                    if idx >= 0:
                        rd['purity'].setCurrentIndex(idx)
                    else:
                        rd['purity'].setCurrentText(purity)
                # Set rate from catalog item
                rate = float(item.get('rate') or 0)
                if rate:
                    rd['rate'].setValue(rate)
                # Jump straight to HUID (purity & rate already filled)
                QTimer.singleShot(0, lambda: self._focus_and_select(rd['huid']))
                return
        # Default: advance to HUID field
        QTimer.singleShot(0, lambda: self._focus_and_select(rd['huid']))

    def eventFilter(self, obj, event):
        """Enter key on any item-chain widget advances to the next; Enter on last adds a new row."""
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if hasattr(obj, '_item_rd') and hasattr(obj, '_chain_idx'):
                    rd    = obj._item_rd
                    chain = rd['chain']
                    idx   = obj._chain_idx
                    if idx + 1 < len(chain):
                        QTimer.singleShot(0, lambda n=chain[idx + 1]: self._focus_and_select(n))
                    else:
                        QTimer.singleShot(0, self._append_item_row)
                    return False   # let widget also commit its value
        return super().eventFilter(obj, event)

    def _refresh_inv_number(self):
        prefix = AppConfig.invoice_prefix()
        last   = AppConfig.last_invoice_number()
        self._inv_num_lbl.setText(f"Next: {prefix}-{last+1:04d}")

    def _recalc_totals(self):
        subtotal = sum(i.get("total", 0) for i in self._items)
        cgst_pct = self.spn_cgst.value()
        sgst_pct = self.spn_sgst.value()
        igst_pct = self.spn_igst.value()
        cgst_amt = round(subtotal * cgst_pct / 100, 2)
        sgst_amt = round(subtotal * sgst_pct / 100, 2)
        igst_amt = round(subtotal * igst_pct / 100, 2)
        grand    = round(subtotal + cgst_amt + sgst_amt + igst_amt, 2)

        self._grand_total = grand
        self.lbl_subtotal.setText(format_currency(subtotal))
        self.lbl_cgst_amt.setText(format_currency(cgst_amt))
        self.lbl_sgst_amt.setText(format_currency(sgst_amt))
        self.lbl_igst_amt.setText(format_currency(igst_amt))
        self.lbl_grand.setText(format_currency(grand))
        self._recalc_due()

    def _recalc_due(self, *_):
        """Due = Grand Total − sum of all payment modes received."""
        def _v(le):
            try: return float(le.text())
            except ValueError: return 0.0
        paid = _v(self.txt_cash) + _v(self.txt_card) + _v(self.txt_cheque) + _v(self.txt_upi)
        due  = round(max(0.0, getattr(self, '_grand_total', 0.0) - paid), 2)
        self.txt_due.setText(f"{due:.2f}")

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
        igst_pct = self.spn_igst.value()
        cgst_amt = round(subtotal * cgst_pct / 100, 2)
        sgst_amt = round(subtotal * sgst_pct / 100, 2)
        igst_amt = round(subtotal * igst_pct / 100, 2)
        grand    = round(subtotal + cgst_amt + sgst_amt + igst_amt, 2)

        return {
            "customer_name":    self.txt_cname.text().strip(),
            "customer_mobile":  self.txt_cmobile.text().strip(),
            "customer_email":   self.txt_cemail.text().strip(),
            "customer_address": self.txt_caddr.text().strip(),
            "customer_gst":     self.txt_cust_gst.text().strip(),
            "customer_aadhaar": self.txt_aadhaar.text().strip(),
            "customer_pan":     self.txt_pan.text().strip(),
            "items":            list(self._items),
            "subtotal":         round(subtotal, 2),
            "cgst_percent":     cgst_pct,
            "sgst_percent":     sgst_pct,
            "igst_percent":     igst_pct,
            "cgst_amount":      cgst_amt,
            "sgst_amount":      sgst_amt,
            "igst_amount":      igst_amt,
            "grand_total":      grand,
            "cash_paid":        float(self.txt_cash.text()   or 0),
            "card_paid":        float(self.txt_card.text()   or 0),
            "card_details":     self.txt_card_details.text().strip(),
            "cheque_paid":      float(self.txt_cheque.text() or 0),
            "cheque_details":   self.txt_cheque_details.text().strip(),
            "upi_paid":         float(self.txt_upi.text()    or 0),
            "due_amount":       float(self.txt_due.text()    or 0),
            "due_date":         self.txt_due_date.text().strip(),
            "remarks":          self.txt_remarks.text().strip(),
            "notes":            self.txt_notes.text().strip(),
            "tax_percent":      cgst_pct + sgst_pct + igst_pct,
            "tax_amount":       cgst_amt + sgst_amt + igst_amt,
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

    # ── Quick-Add helpers ─────────────────────────────────────

    def _quick_add_item(self):
        """Compact dialog: create a catalog item and optionally fill it into this invoice."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Quick Add — New Item")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet("QDialog{background:#f5f6fa;}")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(18, 16, 18, 16)
        vl.setSpacing(10)

        hint = QLabel(
            "Fill in the details below. "
            "<b>Save &amp; Add to Invoice</b> will also insert this item into the current bill."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7f8c8d;font-size:11px;")
        vl.addWidget(hint)

        def _lbl(t):
            l = QLabel(t); l.setStyleSheet("font-weight:600;font-size:11px;color:#555;")
            return l

        def _le(ph=""):
            e = QLineEdit(); e.setPlaceholderText(ph); e.setFixedHeight(34)
            e.setStyleSheet(
                "QLineEdit{border:1px solid #ced4da;border-radius:5px;"
                "padding:0 10px;font-size:13px;background:white;}"
                "QLineEdit:focus{border:2px solid #3498db;background:#eaf6fd;}"
            )
            return e

        def _dspn(val=0.0):
            s = QDoubleSpinBox()
            s.setRange(0, 9_999_999); s.setDecimals(2); s.setValue(val)
            s.setFixedHeight(34); s.setButtonSymbols(QAbstractSpinBox.NoButtons)
            s.setStyleSheet(
                "QDoubleSpinBox{border:1px solid #ced4da;border-radius:5px;"
                "padding:0 10px;font-size:13px;background:white;}"
                "QDoubleSpinBox:focus{border:2px solid #3498db;background:#eaf6fd;}"
            )
            return s

        txt_name   = _le("Item name *  (e.g. Gold Necklace)")
        txt_code   = _le("Shortcut code  (e.g. GN1)")
        txt_purity = _le("Purity  (e.g. 22Kt)")
        spn_rate   = _dspn()

        metals = get_metals()
        cmb_metal = QComboBox(); cmb_metal.setFixedHeight(34)
        cmb_metal.setStyleSheet(
            "QComboBox{border:1px solid #ced4da;border-radius:5px;"
            "padding:0 8px;font-size:13px;background:white;}"
            "QComboBox::drop-down{border:none;}"
        )
        cmb_metal.addItem("(no metal)")
        for m in metals:
            cmb_metal.addItem(f"{m['name']} – {m['purity']}", m.get("id"))

        def _on_metal(idx):
            if idx > 0 and idx - 1 < len(metals):
                m = metals[idx - 1]
                txt_purity.setText(m.get("purity", ""))
                spn_rate.setValue(m.get("rate", 0.0))
        cmb_metal.currentIndexChanged.connect(_on_metal)

        fl = QFormLayout(); fl.setSpacing(8)
        fl.addRow(_lbl("Item Name *"), txt_name)
        fl.addRow(_lbl("Code"),        txt_code)
        fl.addRow(_lbl("Metal"),       cmb_metal)
        fl.addRow(_lbl("Purity"),      txt_purity)
        fl.addRow(_lbl("Rate (₹/g)"), spn_rate)
        vl.addLayout(fl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_fill = QPushButton("💾  Save && Add to Invoice")
        btn_fill.setFixedHeight(38)
        btn_fill.setStyleSheet(
            "QPushButton{background:#f39c12;color:white;border-radius:5px;"
            "font-weight:bold;border:none;padding:0 18px;}"
            "QPushButton:hover{background:#e67e22;}"
        )
        btn_only = QPushButton("Save Only")
        btn_only.setFixedHeight(38)
        btn_only.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:5px;"
            "border:none;padding:0 14px;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setStyleSheet(
            "QPushButton{background:#bdc3c7;color:#2c3e50;border-radius:5px;"
            "border:none;padding:0 14px;}"
        )
        btn_fill.clicked.connect(lambda: dlg.done(2))
        btn_only.clicked.connect(lambda: dlg.done(1))
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_fill); btn_row.addWidget(btn_only); btn_row.addWidget(btn_cancel)
        vl.addLayout(btn_row)

        result = dlg.exec()
        if result == 0:
            return

        name   = txt_name.text().strip()
        code   = txt_code.text().strip().upper()
        purity = txt_purity.text().strip()
        rate   = spn_rate.value()
        if not name:
            QMessageBox.warning(self, "Validation", "Item Name is required.")
            return

        midx     = cmb_metal.currentIndex()
        metal_id = cmb_metal.itemData(midx) if midx > 0 else ""
        labour   = 0.0
        if metal_id:
            m = next((x for x in metals if x.get("id") == metal_id), None)
            if m: labour = m.get("labour", 0.0)

        ok = add_catalog_item(name, "", purity, code, "", metal_id, rate, labour)
        if not ok:
            QMessageBox.warning(
                self, "Duplicate",
                f'"{name}" already exists, or code "{code}" is already taken.'
            )
            return

        self._refresh_item_completers()

        if result == 2:   # Save & Add to Invoice
            # Find first empty row; if none exists, append one
            target_rd = None
            for rd in self._row_widgets:
                if not rd['name'].text().strip():
                    target_rd = rd; break
            if target_rd is None:
                self._append_item_row()
                target_rd = self._row_widgets[-1]
            QTimer.singleShot(30, lambda: self._fill_item_row(target_rd, name, purity, rate))
        else:
            code_hint = f'  Use code "<b>{code}</b>" to auto-fill it.' if code else ""
            QMessageBox.information(
                self, "Saved",
                f'"{name}" added to the catalog.{code_hint}'
            )

    def _fill_item_row(self, rd: dict, name: str, purity: str, rate: float):
        rd['name'].setText(name)
        if purity:
            idx = rd['purity'].findText(purity)
            if idx >= 0:
                rd['purity'].setCurrentIndex(idx)
            else:
                rd['purity'].setCurrentText(purity)
        if rate:
            rd['rate'].setValue(rate)
        self._rebuild_items_from_table()
        rd['gwt'].setFocus()

    def _quick_add_metal(self):
        """Compact dialog: add a metal / purity / rate entry to the rate card."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Quick Add — Metal Rate")
        dlg.setMinimumWidth(360)
        dlg.setStyleSheet("QDialog{background:#f5f6fa;}")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(18, 16, 18, 16)
        vl.setSpacing(10)

        hint = QLabel("Add a new metal / purity combination with its current market rate.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7f8c8d;font-size:11px;")
        vl.addWidget(hint)

        def _lbl(t):
            l = QLabel(t); l.setStyleSheet("font-weight:600;font-size:11px;color:#555;")
            return l

        def _le(ph=""):
            e = QLineEdit(); e.setPlaceholderText(ph); e.setFixedHeight(34)
            e.setStyleSheet(
                "QLineEdit{border:1px solid #ced4da;border-radius:5px;"
                "padding:0 10px;font-size:13px;background:white;}"
                "QLineEdit:focus{border:2px solid #3498db;background:#eaf6fd;}"
            )
            return e

        def _dspn():
            s = QDoubleSpinBox()
            s.setRange(0, 9_999_999); s.setDecimals(2)
            s.setFixedHeight(34); s.setButtonSymbols(QAbstractSpinBox.NoButtons)
            s.setStyleSheet(
                "QDoubleSpinBox{border:1px solid #ced4da;border-radius:5px;"
                "padding:0 10px;font-size:13px;background:white;}"
                "QDoubleSpinBox:focus{border:2px solid #3498db;background:#eaf6fd;}"
            )
            return s

        txt_name   = _le("e.g. Gold")
        txt_purity = _le("e.g. 22Kt")
        spn_rate   = _dspn()
        spn_labour = _dspn()

        # Enter-key navigation inside dialog
        txt_name.returnPressed.connect(txt_purity.setFocus)
        txt_purity.returnPressed.connect(spn_rate.setFocus)

        fl = QFormLayout(); fl.setSpacing(8)
        fl.addRow(_lbl("Metal Name *"),  txt_name)
        fl.addRow(_lbl("Purity *"),      txt_purity)
        fl.addRow(_lbl("Rate (₹/g) *"), spn_rate)
        fl.addRow(_lbl("Labour (₹/g)"), spn_labour)
        vl.addLayout(fl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_save = QPushButton("💾  Save Metal")
        btn_save.setFixedHeight(38)
        btn_save.setStyleSheet(
            "QPushButton{background:#16a085;color:white;border-radius:5px;"
            "font-weight:bold;border:none;padding:0 18px;}"
            "QPushButton:hover{background:#138d75;}"
        )
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setStyleSheet(
            "QPushButton{background:#bdc3c7;color:#2c3e50;border-radius:5px;"
            "border:none;padding:0 14px;}"
        )
        btn_save.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_save); btn_row.addWidget(btn_cancel)
        vl.addLayout(btn_row)

        if dlg.exec() != QDialog.Accepted:
            return

        name_v   = txt_name.text().strip()
        purity_v = txt_purity.text().strip()
        if not name_v or not purity_v:
            QMessageBox.warning(self, "Validation", "Metal Name and Purity are required.")
            return

        _add_metal_rec(name_v, purity_v, spn_rate.value(), spn_labour.value())
        QMessageBox.information(
            self, "Saved",
            f'"{name_v} – {purity_v}" added.\n'
            "Go to Settings → Metals to edit it any time."
        )

    def _refresh_item_completers(self):
        """Update the autocomplete list on every item name field in the current table."""
        names = get_catalog_names()
        for rd in self._row_widgets:
            w = rd['name']
            c = QCompleter(names, w)
            c.setCaseSensitivity(Qt.CaseInsensitive)
            c.setFilterMode(Qt.MatchContains)
            w.setCompleter(c)

    def _clear_all(self):
        self.txt_cname.clear()
        self.txt_cmobile.clear()
        self.txt_cemail.clear()
        self.txt_caddr.clear()
        self.txt_cust_gst.clear()
        self.txt_aadhaar.clear()
        self.txt_pan.clear()
        self.txt_notes.clear()
        self.txt_due_date.clear()
        self.txt_remarks.clear()
        self.txt_card_details.clear()
        self.txt_cheque_details.clear()
        for f in (self.txt_cash, self.txt_card, self.txt_cheque,
                  self.txt_upi, self.txt_due):
            f.clear()
        self._reset_items_table()
        self.spn_cgst.setValue(1.5)
        self.spn_sgst.setValue(1.5)
        self.spn_igst.setValue(0.0)
        self._recalc_totals()
        self._refresh_inv_number()

    def refresh(self):
        self._refresh_inv_number()

        # Refresh customer cache + completer so new customers show up
        self._customers_cache = get_all_customers()
        mobiles = [c.get("mobile", "") for c in self._customers_cache if c.get("mobile")]
        completer = QCompleter(mobiles, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.txt_cmobile.setCompleter(completer)