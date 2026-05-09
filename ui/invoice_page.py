# ============================================================
# ui/invoice_page.py - Invoice / Billing Page (Jewelry Format)
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox,
    QComboBox, QFrame, QScrollArea, QHeaderView, QAbstractItemView,
    QCompleter, QAbstractSpinBox, QDialog, QDateEdit, QApplication
)
from PyQt5.QtCore import Qt, QEvent, QTimer, QDate, QPoint, QObject
from PyQt5.QtGui import QFont, QDoubleValidator
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
from app.config import AppConfig
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf
from services.invoice_service import create_invoice, update_invoice
from services.customer_service import get_all_customers, update_customer
from services.item_catalog_service import (
    get_item_by_code, get_item_by_name, get_names as get_catalog_names, add_catalog_item
)
from services.metal_service import get_metals, get_metal_by_id, add_metal as _add_metal_rec


PURITY_OPTIONS = ["22Kt", "18Kt", "14Kt", "92.5", "99.9", "60-70", "Other"]


class _EnterNav(QObject):
    """Enter-key navigation chain for dialog fields.
    Moves focus field-by-field; calls on_last() when Enter is pressed on the final field.
    Skips interception while a QCompleter popup is open.
    """
    def __init__(self, chain, on_last=None, parent=None):
        super().__init__(parent)
        self._nxt = {}
        for i, w in enumerate(chain):
            self._nxt[id(w)] = chain[i + 1] if i + 1 < len(chain) else None
            w.installEventFilter(self)
        self._on_last = on_last

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Don't intercept while an autocomplete popup is showing
            if hasattr(obj, 'completer') and obj.completer() and obj.completer().popup().isVisible():
                return False
            key = id(obj)
            if key not in self._nxt:
                return False
            nxt = self._nxt[key]
            if nxt is not None:
                nxt.setFocus()
                QTimer.singleShot(0, nxt.selectAll if hasattr(nxt, 'selectAll') else lambda: None)
                return True
            if self._on_last:
                self._on_last()
                return True
        return False


class InvoicePage(QWidget):
    def __init__(self):
        super().__init__()
        self._items: list[dict] = []
        self._last_invoice: dict = {}
        self._grand_total: float = 0.0
        self._edit_mode: bool = False
        self._editing_invoice_id: str = ""
        self._editing_invoice_number: str = ""
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 6)
        root.setSpacing(6)

        # Title bar
        top = QHBoxLayout()
        self._title_lbl = QLabel("🧾  New Invoice")
        self._title_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._inv_num_lbl = QLabel()
        self._inv_num_lbl.setStyleSheet("color: #f39c12; font-size: 12px; font-weight: bold;")

        # Invoice date — defaults to today, editable (supports back-dating)
        _date_lbl = QLabel("Date:")
        _date_lbl.setStyleSheet("color:#555; font-size:11px; font-weight:600;")
        self.dte_invoice = QDateEdit(QDate.currentDate())
        self.dte_invoice.setCalendarPopup(True)
        self.dte_invoice.setDisplayFormat("dd-MM-yyyy")
        self.dte_invoice.setMinimumHeight(26)
        self.dte_invoice.setMaximumWidth(130)
        self.dte_invoice.setStyleSheet(
            "QDateEdit{border:1px solid #ced4da;border-radius:4px;padding:1px 6px;font-size:12px;}"
            "QDateEdit:focus{border:2px solid #3498db;background:#eaf6fd;}"
        )

        btn_clear = QPushButton("🔄  New / Clear")
        btn_clear.setStyleSheet(
            "QPushButton { background:#7f8c8d; color:white; border-radius:5px; padding:4px 12px; font-size:12px; }"
            "QPushButton:hover { background:#95a5a6; }"
        )
        btn_clear.clicked.connect(self._clear_all)

        top.addWidget(self._title_lbl)
        top.addStretch()
        top.addWidget(self._inv_num_lbl)
        top.addSpacing(12)
        top.addWidget(_date_lbl)
        top.addWidget(self.dte_invoice)
        top.addSpacing(8)
        top.addWidget(btn_clear)
        root.addLayout(top)

        # ── Customer Section (two rows) ──────────────────────────
        cust_grp = QGroupBox("Customer Details")
        cv = QVBoxLayout(cust_grp)
        cv.setSpacing(3)
        cv.setContentsMargins(8, 4, 8, 4)

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
            w.setMinimumHeight(26)
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
            w.setMinimumHeight(26)
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
            "border-radius:6px;margin-top:8px;padding-top:4px;}"
            "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}"
        )
        itl = QVBoxLayout(items_grp)
        itl.setContentsMargins(4, 4, 4, 4)
        itl.setSpacing(2)

        # ── Quick-add toolbar ─────────────────────────────────
        qa_bar = QHBoxLayout()

        btn_add_row = QPushButton("➕  Add Row")
        btn_add_row.setToolTip("Add another item row (Ctrl+D)")
        btn_add_row.setShortcut("Ctrl+D")
        btn_add_row.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:4px;"
            "padding:4px 12px;font-size:11px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        btn_add_row.clicked.connect(self._append_item_row)
        qa_bar.addWidget(btn_add_row)

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

        btn_shortcuts = QPushButton("⌨  Shortcuts")
        btn_shortcuts.setFlat(True)
        btn_shortcuts.setStyleSheet(
            "QPushButton{color:#7f8c8d;border:1px solid #ced4da;border-radius:4px;"
            "padding:4px 10px;font-size:11px;background:#f8f9fa;}"
            "QPushButton:hover{background:#ecf0f1;color:#2c3e50;}"
        )
        btn_shortcuts.setToolTip(
            "Ctrl+D  Add new item row\n"
            "Ctrl+G  Jump to IGST field\n"
            "Ctrl+I  Quick-add catalog item\n"
            "Ctrl+M  Quick-add metal rate"
        )

        def _show_shortcuts():
            popup = QDialog(self)
            popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
            popup.setStyleSheet(
                "QDialog{background:#2c3e50;border:1px solid #1a252f;border-radius:6px;}"
                "QLabel{background:transparent;color:#ecf0f1;font-size:12px;}"
            )
            pl = QVBoxLayout(popup)
            pl.setContentsMargins(16, 12, 16, 12)
            pl.setSpacing(8)

            hdr = QLabel("Keyboard Shortcuts")
            hdr.setFont(QFont("Segoe UI", 10, QFont.Bold))
            hdr.setStyleSheet("color:#f39c12;font-size:12px;")
            pl.addWidget(hdr)

            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("background:#455a64;max-height:1px;border:none;")
            pl.addWidget(sep)

            for key, desc in [
                ("Ctrl+D", "Add new item row"),
                ("Ctrl+G", "Jump to IGST field"),
                ("Ctrl+I", "Quick-add catalog item"),
                ("Ctrl+M", "Quick-add metal rate"),
                ("Enter",  "Move to next field in row"),
            ]:
                row = QHBoxLayout(); row.setSpacing(12)
                k = QLabel(key)
                k.setFixedWidth(76)
                k.setAlignment(Qt.AlignCenter)
                k.setStyleSheet(
                    "color:#3498db;font-weight:bold;font-size:11px;"
                    "background:#1a252f;border-radius:3px;padding:1px 4px;"
                )
                d = QLabel(desc)
                row.addWidget(k); row.addWidget(d); row.addStretch()
                pl.addLayout(row)

            popup.adjustSize()
            pw = popup.width()
            ph = popup.height()

            # Right-align popup to the button's right edge, appear below it
            btn_global = btn_shortcuts.mapToGlobal(QPoint(0, 0))
            x = btn_global.x() + btn_shortcuts.width() - pw
            y = btn_global.y() + btn_shortcuts.height() + 4

            # Clamp to screen so it never goes off any edge
            screen = QApplication.desktop().availableGeometry(btn_shortcuts)
            x = max(screen.left(), min(x, screen.right() - pw))
            if y + ph > screen.bottom():
                y = btn_global.y() - ph - 4   # flip above button if no room below
            y = max(screen.top(), y)

            popup.move(x, y)
            popup.show()

        btn_shortcuts.clicked.connect(_show_shortcuts)

        qa_bar.addWidget(btn_qi)
        qa_bar.addWidget(btn_qm)
        qa_bar.addWidget(btn_shortcuts)
        itl.addLayout(qa_bar)

        self.tbl_items = QTableWidget()
        self.tbl_items.setColumnCount(15)
        self.tbl_items.setHorizontalHeaderLabels([
            "#", "Tag/RFID", "Item Name", "HUID/Remarks", "Purity",
            "GWT g", "Less g", "NWT g",
            "Pcs", "Rate ₹/g", "MK", "MK ₹", "Other ₹", "Total ₹", ""
        ])
        hdr = self.tbl_items.horizontalHeader()
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        # col 0 (#) and col 14 (delete) are truly fixed; all others are Interactive
        _fixed_cols       = {0: 28, 14: 30}
        _interactive_cols = {1: 90, 3: 150, 4: 78, 5: 80, 6: 68, 7: 80,
                             8: 48, 9: 96, 10: 114, 11: 72, 12: 84, 13: 102}
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
        self.tbl_items.setMinimumHeight(80)
        self.tbl_items.verticalHeader().setDefaultSectionSize(32)

        self._row_widgets: list[dict] = []
        self._append_item_row()   # start with one blank row

        itl.addWidget(self.tbl_items)
        root.addWidget(items_grp, 1)

        # ── Tax + Payment ─────────────────────────────────────
        bottom = QHBoxLayout(); bottom.setSpacing(8)

        # ── Payment Details ───────────────────────────────────
        pay_grp = QGroupBox("Payment Details")
        pfl = QFormLayout(pay_grp)
        pfl.setSpacing(4)
        pfl.setLabelAlignment(Qt.AlignRight)
        pfl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        _num_validator = QDoubleValidator(0.0, 9999999.0, 2)
        _num_validator.setNotation(QDoubleValidator.StandardNotation)

        def _money_edit(placeholder="0.00"):
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            e.setValidator(_num_validator)
            e.setMinimumHeight(26)
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
        self.txt_card_details.setMinimumHeight(26)
        pfl.addRow("Card:", _pay_row(self.txt_card, self.txt_card_details))

        self.txt_cheque = _money_edit()
        self.txt_cheque_details = QLineEdit()
        self.txt_cheque_details.setPlaceholderText("Cheque no. / bank")
        self.txt_cheque_details.setMinimumHeight(26)
        pfl.addRow("Cheque:", _pay_row(self.txt_cheque, self.txt_cheque_details))

        self.txt_upi = _money_edit()
        pfl.addRow("UPI:", _single_row(self.txt_upi))

        self.txt_old_purchase = _money_edit()
        _op_lbl = QLabel("(-) Old Purchase:")
        _op_lbl.setStyleSheet("color:#e67e22; font-weight:600;")
        pfl.addRow(_op_lbl, _single_row(self.txt_old_purchase))

        self.txt_advance = _money_edit()
        _adv_lbl = QLabel("(-) Advance:")
        _adv_lbl.setStyleSheet("color:#e67e22; font-weight:600;")
        pfl.addRow(_adv_lbl, _single_row(self.txt_advance))

        self.txt_roundoff = _money_edit("0.00")
        _ro_auto = QPushButton("Auto")
        _ro_auto.setFixedHeight(26)
        _ro_auto.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:4px;"
            "padding:1px 8px;font-size:10px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        _ro_auto.clicked.connect(self._auto_roundoff)
        _ro_w = QWidget(); _ro_w.setStyleSheet("background:transparent;")
        _ro_h = QHBoxLayout(_ro_w); _ro_h.setContentsMargins(0, 0, 0, 0); _ro_h.setSpacing(4)
        _ro_h.addWidget(_ro_auto)
        _ro_h.addWidget(self.txt_roundoff, 1)
        pfl.addRow("Round Off (-):", _ro_w)

        self.txt_due = QLineEdit("0.00")
        self.txt_due.setReadOnly(True)
        self.txt_due.setMinimumHeight(26)
        self.txt_due.setStyleSheet(
            "QLineEdit { background:#fef9e7; color:#e74c3c; font-weight:bold;"
            " border:1px solid #f9ca24; border-radius:4px; padding:4px 8px; }"
        )
        pfl.addRow("Due Amount:", _single_row(self.txt_due))

        # ── Refund row ────────────────────────────────────────────
        self.txt_refund = _money_edit()
        self.txt_refund.setMinimumHeight(30)
        self.cmb_refund_mode = QComboBox()
        self.cmb_refund_mode.addItems(["Cash", "Card", "UPI", "Cheque", "Bank Transfer", "Other"])
        self.cmb_refund_mode.setMinimumHeight(30)
        self.cmb_refund_mode.setStyleSheet(
            "QComboBox{border:1px solid #ced4da;border-radius:4px;padding:2px 6px;"
            "font-size:12px;background:white;}"
            "QComboBox::drop-down{border:none;width:16px;}"
        )
        _ref_w = QWidget(); _ref_w.setStyleSheet("background:transparent;")
        _ref_w.setMinimumHeight(30)
        _ref_h = QHBoxLayout(_ref_w); _ref_h.setContentsMargins(0, 0, 0, 0); _ref_h.setSpacing(4)
        _ref_rupee = QLabel("₹"); _ref_rupee.setStyleSheet("color:#555;font-weight:600;")
        _ref_h.addWidget(_ref_rupee)
        _ref_h.addWidget(self.txt_refund, 1)
        _ref_h.addWidget(self.cmb_refund_mode, 1)
        _ref_lbl = QLabel("Refund Given:")
        _ref_lbl.setStyleSheet("color:#27ae60; font-weight:600;")
        pfl.addRow(_ref_lbl, _ref_w)

        self.txt_due_date = QLineEdit()
        self.txt_due_date.setPlaceholderText("e.g. 31 Dec 25")
        self.txt_due_date.setMinimumHeight(26)
        pfl.addRow("Due Date:", self.txt_due_date)

        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Remarks (optional)")
        self.txt_remarks.setMinimumHeight(26)
        pfl.addRow("Remarks:", self.txt_remarks)

        # Auto-recalc due whenever a payment field changes
        for f in (self.txt_cash, self.txt_card, self.txt_cheque, self.txt_upi,
                  self.txt_old_purchase, self.txt_advance, self.txt_roundoff):
            f.textChanged.connect(self._recalc_due)

        # Enter-key chain for payment section — uses event filter (not returnPressed)
        # because returnPressed is blocked by QDoubleValidator on empty/zero fields.
        _pay_chain = [
            self.txt_cash, self.txt_card, self.txt_card_details,
            self.txt_cheque, self.txt_cheque_details,
            self.txt_upi, self.txt_old_purchase, self.txt_advance,
            self.txt_roundoff, self.txt_refund, self.txt_due_date, self.txt_remarks,
        ]
        for _pi, _pw in enumerate(_pay_chain):
            _pw._pay_chain = _pay_chain
            _pw._pay_idx   = _pi
            _pw.installEventFilter(self)

        bottom.addWidget(pay_grp, 3)

        # ── Totals / Tax ──────────────────────────────────────
        totals_frame = QFrame()
        totals_frame.setStyleSheet(
            "QFrame { background:white; border:1px solid #e0e0e0; border-radius:6px; padding:6px; }"
        )
        # Outer VBox: form rows on top, stretch, hint pinned to bottom
        _totals_vbox = QVBoxLayout(totals_frame)
        _totals_vbox.setContentsMargins(0, 0, 0, 0)
        _totals_vbox.setSpacing(0)

        _tax_form_w = QWidget(); _tax_form_w.setStyleSheet("background:transparent;")
        tfl = QFormLayout(_tax_form_w)
        tfl.setLabelAlignment(Qt.AlignRight)
        tfl.setSpacing(5)
        tfl.setContentsMargins(6, 6, 6, 4)
        tfl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        def _tax_spn(default=0.0):
            s = QDoubleSpinBox()
            s.setRange(0, 28); s.setDecimals(2); s.setSuffix(" %"); s.setValue(default)
            s.setMinimumHeight(26); s.setMaximumWidth(80)
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
        self.lbl_grand.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_grand.setStyleSheet("color:#27ae60;")
        self.lbl_grand.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        def _on_igst_changed(v):
            if v > 0:
                self.spn_cgst.blockSignals(True)
                self.spn_sgst.blockSignals(True)
                self.spn_cgst.setValue(0.0)
                self.spn_sgst.setValue(0.0)
                self.spn_cgst.blockSignals(False)
                self.spn_sgst.blockSignals(False)
            self._recalc_totals()

        def _on_cgst_sgst_changed(v):
            if v > 0:
                self.spn_igst.blockSignals(True)
                self.spn_igst.setValue(0.0)
                self.spn_igst.blockSignals(False)
            self._recalc_totals()

        self.spn_igst.valueChanged.connect(_on_igst_changed)
        self.spn_cgst.valueChanged.connect(_on_cgst_sgst_changed)
        self.spn_sgst.valueChanged.connect(_on_cgst_sgst_changed)

        tfl.addRow("Gross Amount:", self.lbl_subtotal)
        tfl.addRow("CGST:",  _tax_row_widget(self.spn_cgst, self.lbl_cgst_amt))
        tfl.addRow("SGST:",  _tax_row_widget(self.spn_sgst, self.lbl_sgst_amt))
        tfl.addRow("IGST:",  _tax_row_widget(self.spn_igst, self.lbl_igst_amt))
        tfl.addRow("NET PAYABLE:", self.lbl_grand)

        _totals_vbox.addWidget(_tax_form_w)
        _totals_vbox.addStretch()

        # Info hint — pinned to the bottom of the totals card
        _igst_hint = QLabel("  ⌨  Ctrl+G  —  Edit IGST")
        _igst_hint.setAlignment(Qt.AlignCenter)
        _igst_hint.setFixedHeight(26)
        _igst_hint.setStyleSheet(
            "background:#eaf4fb;"
            "color:#1a5276;"
            "border:1px solid #aed6f1;"
            "border-radius:4px;"
            "font-size:11px;"
            "font-weight:600;"
            "padding:0 6px;"
            "margin:0 6px 6px 6px;"
        )
        _igst_hint.setCursor(Qt.PointingHandCursor)
        _igst_hint.mousePressEvent = lambda _: self._focus_igst()
        _totals_vbox.addWidget(_igst_hint)

        bottom.addWidget(totals_frame, 2)

        root.addLayout(bottom)

        # Notes
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel("Notes:"))
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Any special notes (optional)")
        self.txt_notes.setMinimumHeight(26)
        notes_row.addWidget(self.txt_notes)
        root.addLayout(notes_row)

        # ── Action Buttons ────────────────────────────────────
        act_row = QHBoxLayout(); act_row.setSpacing(8)

        btn_preview = QPushButton("👁  Preview PDF")
        btn_preview.setStyleSheet(
            "QPushButton { background:#8e44ad; color:white; border-radius:5px; padding:6px 14px; font-weight:bold; }"
            "QPushButton:hover { background:#7d3c98; }"
        )
        btn_preview.clicked.connect(self._preview_invoice)

        self._btn_save = QPushButton("💾  Save Invoice")
        self._btn_save.setStyleSheet(
            "QPushButton { background:#2980b9; color:white; border-radius:5px; padding:6px 14px; font-weight:bold; }"
            "QPushButton:hover { background:#2471a3; }"
        )
        self._btn_save.clicked.connect(self._save_invoice)

        self._btn_print = QPushButton("🖨  Save && Print PDF")
        self._btn_print.setStyleSheet(
            "QPushButton { background:#f39c12; color:white; border-radius:5px; padding:6px 14px; font-weight:bold; }"
            "QPushButton:hover { background:#e67e22; }"
        )
        self._btn_print.clicked.connect(self._save_and_print)

        act_row.addStretch()
        act_row.addWidget(btn_preview)
        act_row.addWidget(self._btn_save)
        act_row.addWidget(self._btn_print)
        root.addLayout(act_row)

        # Ctrl+G → jump to IGST spinner
        _igst_sc = QShortcut(QKeySequence("Ctrl+G"), self)
        _igst_sc.setContext(Qt.WidgetWithChildrenShortcut)
        _igst_sc.activated.connect(self._focus_igst)

        self._refresh_inv_number()

    def _focus_igst(self):
        self.spn_igst.setFocus()
        self.spn_igst.selectAll()

    # ── Customer Autocomplete & Auto-update ──────────────────────
    def _setup_customer_autocomplete(self):
        self._customers_cache = get_all_customers()
        self._selected_customer_id = ""
        self._rebuild_customer_completers()
        self.txt_cmobile.textChanged.connect(self._autofill_by_mobile_text)
        for field in (self.txt_cname, self.txt_cmobile, self.txt_caddr,
                      self.txt_cemail, self.txt_aadhaar, self.txt_pan):
            field.editingFinished.connect(self._on_customer_field_edited)

    def _rebuild_customer_completers(self):
        """Rebuild completers on both mobile and name fields from the current cache."""
        mobiles = [c.get("mobile", "") for c in self._customers_cache if c.get("mobile")]
        mob_c = QCompleter(mobiles, self)
        mob_c.setCaseSensitivity(Qt.CaseInsensitive)
        mob_c.setFilterMode(Qt.MatchContains)
        mob_c.activated.connect(self._on_mobile_chosen)
        self.txt_cmobile.setCompleter(mob_c)

        names = [c.get("customer_name", "") for c in self._customers_cache if c.get("customer_name")]
        name_c = QCompleter(names, self)
        name_c.setCaseSensitivity(Qt.CaseInsensitive)
        name_c.setFilterMode(Qt.MatchContains)
        name_c.activated.connect(self._on_name_chosen)
        self.txt_cname.setCompleter(name_c)

    def _autofill_from_customer(self, c: dict):
        """Fill all customer fields from a record and track the selected customer ID."""
        self._selected_customer_id = c.get("customer_id", "")
        for field, val in (
            (self.txt_cname,   c.get("customer_name", "")),
            (self.txt_cmobile, c.get("mobile",        "")),
            (self.txt_caddr,   c.get("address",       "")),
            (self.txt_cemail,  c.get("email",         "")),
            (self.txt_aadhaar, c.get("aadhaar",       "")),
            (self.txt_pan,     c.get("pan",           "")),
        ):
            field.blockSignals(True)
            field.setText(val)
            field.blockSignals(False)

    def _on_mobile_chosen(self, text: str):
        text = text.strip()
        for c in self._customers_cache:
            if c.get("mobile", "") == text:
                self._autofill_from_customer(c)
                return

    def _on_name_chosen(self, text: str):
        text = text.strip()
        for c in self._customers_cache:
            if c.get("customer_name", "") == text:
                self._autofill_from_customer(c)
                return

    def _autofill_by_mobile_text(self, text: str):
        """Real-time exact-match autofill as the user types in the mobile field."""
        text = text.strip()
        if len(text) < 6:
            return
        for c in self._customers_cache:
            if c.get("mobile", "") == text:
                self._autofill_from_customer(c)
                return

    def _on_customer_field_edited(self):
        """When any customer field loses focus, update the customer record if one is selected."""
        if not self._selected_customer_id:
            return
        update_customer(self._selected_customer_id, {
            "customer_name": self.txt_cname.text().strip(),
            "mobile":        self.txt_cmobile.text().strip(),
            "address":       self.txt_caddr.text().strip(),
            "email":         self.txt_cemail.text().strip(),
            "aadhaar":       self.txt_aadhaar.text().strip(),
            "pan":           self.txt_pan.text().strip(),
        })
        self._customers_cache = get_all_customers()
        self._rebuild_customer_completers()

    # ── Inline-table helpers ──────────────────────────────────
    def _append_item_row(self):
        """Append a new editable row; focus its Item Name field."""
        row_idx = self.tbl_items.rowCount()
        self.tbl_items.insertRow(row_idx)
        self.tbl_items.setRowHeight(row_idx, 32)

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
        w_lwt   = _dspn(dec=3)   # less / deduction weight
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
        w_mk_btn.setFixedSize(24, 30)
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
            lbl_num, w_tag, w_name, w_huid, w_purity, w_gwt, w_lwt, w_nwt,
            w_qty, w_rate, mk_wrap, w_mk_lbl, w_other, w_total_lbl, w_del
        ]):
            self.tbl_items.setCellWidget(row_idx, col, widget)

        rd = {
            'tag': w_tag, 'name': w_name, 'huid': w_huid,
            'purity': w_purity,
            'gwt': w_gwt, 'lwt': w_lwt, 'nwt': w_nwt,
            'qty': w_qty,   'rate': w_rate,
            'mk_btn': w_mk_btn, 'mk_spn': w_mk_spn,
            'mk_lbl': w_mk_lbl, 'mk_is_pct': mk_is_pct,
            'other': w_other, 'total_lbl': w_total_lbl,
        }
        self._row_widgets.append(rd)

        # Enter-key chain: tag→name→huid→purity→gwt→lwt→nwt→qty→rate→mk_spn→other→payment
        chain = [w_tag, w_name, w_huid, w_purity, w_gwt, w_lwt, w_nwt, w_qty, w_rate, w_mk_spn, w_other]
        rd['chain'] = chain
        for ci, w in enumerate(chain):
            if isinstance(w, QComboBox) and w.isEditable():
                # Editable QComboBox key events go to its internal QLineEdit, not the
                # widget itself, so installEventFilter on the combo won't fire. Use
                # returnPressed on the internal line edit instead.
                nxt = chain[ci + 1] if ci + 1 < len(chain) else None
                if nxt:
                    w.lineEdit().returnPressed.connect(
                        lambda _nw=nxt: QTimer.singleShot(0, lambda: self._focus_and_select(_nw))
                    )
            elif not isinstance(w, QLineEdit):
                w._item_rd   = rd
                w._chain_idx = ci
                w.installEventFilter(self)
        w_tag.returnPressed.connect(lambda _rd=rd: self._focus_and_select(_rd['name']))
        w_name.returnPressed.connect(lambda _rd=rd: self._name_code_lookup(_rd))
        w_huid.returnPressed.connect(lambda _rd=rd: self._focus_and_select(_rd['purity']))

        # When a name is chosen from the autocomplete dropdown, fill purity + rate
        if w_name.completer():
            w_name.completer().activated.connect(
                lambda name, _rd=rd: self._autofill_item_by_name(name, _rd)
            )

        # GWT or LWT change → NWT = GWT − LWT (clamped to 0)
        def _sync_nwt(_rd=rd):
            nwt = max(0.0, round(_rd['gwt'].value() - _rd['lwt'].value(), 3))
            _rd['nwt'].blockSignals(True)
            _rd['nwt'].setValue(nwt)
            _rd['nwt'].blockSignals(False)
            self._row_calc(_rd)
            self._rebuild_items_from_table()
        w_gwt.valueChanged.connect(lambda _: _sync_nwt())
        w_lwt.valueChanged.connect(lambda _: _sync_nwt())

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

            _cat_item   = get_item_by_name(name)
            _metal_id   = _cat_item.get('metal_id', '') if _cat_item else ''
            _category   = _cat_item.get('category', '') if _cat_item else ''
            _metal_name = ''
            if _metal_id:
                _m = get_metal_by_id(_metal_id)
                _metal_name = _m.get('name', '') if _m else ''

            self._items.append({
                'tag':           rd['tag'].text().strip(),
                'name':          name,
                'huid':          rd['huid'].text().strip(),
                'category':      _category,
                'metal':         _metal_name,
                'metal_id':      _metal_id,
                'hsn_code':      '7113',
                'purity':        rd['purity'].currentText(),
                'quantity':      rd['qty'].value(),
                'weight':        gwt,
                'less_weight':   round(rd['lwt'].value(), 3),
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
            for spn in (rd['gwt'], rd['lwt'], rd['nwt'], rd['rate'], rd['mk_spn'], rd['other']):
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
        """On Enter in item name: try code lookup first, then name lookup."""
        text = rd['name'].text().strip()
        if text:
            # 1. Try shortcut code (e.g. "GN1")
            item = get_item_by_code(text)
            if item:
                rd['name'].blockSignals(True)
                rd['name'].setText(item.get('name', text))
                rd['name'].blockSignals(False)
                self._apply_catalog_item(item, rd)
                return

            # 2. Try exact name match (user typed full name or picked via autocomplete + Enter)
            item = get_item_by_name(text)
            if item:
                self._apply_catalog_item(item, rd)
                return

        # No match — just advance to HUID
        QTimer.singleShot(0, lambda: self._focus_and_select(rd['huid']))

    def eventFilter(self, obj, event):
        """Enter key navigation for item-table rows and payment fields."""
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # ── Item table spinbox chain ─────────────────────────
            if hasattr(obj, '_item_rd') and hasattr(obj, '_chain_idx'):
                rd    = obj._item_rd
                chain = rd['chain']
                idx   = obj._chain_idx
                if idx + 1 < len(chain):
                    QTimer.singleShot(0, lambda n=chain[idx + 1]: self._focus_and_select(n))
                else:
                    # Last item field: if this row has a name, start the next row;
                    # if the row is empty, move to the payment section instead.
                    if rd['name'].text().strip():
                        QTimer.singleShot(0, self._append_item_row)
                    else:
                        QTimer.singleShot(0, lambda: self._focus_and_select(self.txt_cash))
                return True   # consume — spinbox value commits on focusOut

            # ── Payment section chain ────────────────────────────
            if hasattr(obj, '_pay_chain') and hasattr(obj, '_pay_idx'):
                chain = obj._pay_chain
                idx   = obj._pay_idx
                if idx + 1 < len(chain):
                    QTimer.singleShot(0, lambda n=chain[idx + 1]: self._focus_and_select(n))
                return False

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
        """Recalculate due/refund when payment amounts change.

        balance = net_payable - total_paid
          balance > 0  →  customer still owes (due amount)
          balance < 0  →  overpaid, auto-fill refund field
          balance = 0  →  fully settled
        """
        def _v(le):
            try: return float(le.text())
            except ValueError: return 0.0
        round_off = _v(self.txt_roundoff)
        paid = (_v(self.txt_cash) + _v(self.txt_card) + _v(self.txt_cheque) + _v(self.txt_upi)
                + _v(self.txt_old_purchase) + _v(self.txt_advance))
        net     = max(0.0, getattr(self, '_grand_total', 0.0) - round_off)
        balance = round(net - paid, 2)

        self.lbl_grand.setText(format_currency(net))

        if balance >= 0:
            self.txt_due.setText(f"{balance:.2f}")
            self.txt_refund.blockSignals(True)
            self.txt_refund.clear()
            self.txt_refund.blockSignals(False)
        else:
            self.txt_due.setText("0.00")
            self.txt_refund.blockSignals(True)
            self.txt_refund.setText(f"{abs(balance):.2f}")
            self.txt_refund.blockSignals(False)

    def _auto_roundoff(self):
        """Fill round-off with the decimal fraction of the current grand total."""
        grand = getattr(self, '_grand_total', 0.0)
        frac  = round(grand % 1, 2)
        self.txt_roundoff.setText(f"{frac:.2f}")

    def _validate(self) -> bool:
        if not self.txt_cmobile.text().strip():
            QMessageBox.warning(self, "Validation", "Customer mobile number is required.")
            self.txt_cmobile.setFocus()
            return False
        if not self.txt_cname.text().strip():
            QMessageBox.warning(self, "Validation", "Customer name is required.")
            self.txt_cname.setFocus()
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
            "invoice_date":     self.dte_invoice.date().toString("yyyy-MM-dd"),
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
            "cash_paid":        float(self.txt_cash.text()         or 0),
            "card_paid":        float(self.txt_card.text()         or 0),
            "card_details":     self.txt_card_details.text().strip(),
            "cheque_paid":      float(self.txt_cheque.text()       or 0),
            "cheque_details":   self.txt_cheque_details.text().strip(),
            "upi_paid":         float(self.txt_upi.text()          or 0),
            "old_purchase":     float(self.txt_old_purchase.text() or 0),
            "advance_paid":     float(self.txt_advance.text()      or 0),
            "round_off":        float(self.txt_roundoff.text()     or 0),
            "due_amount":       float(self.txt_due.text()          or 0),
            "refund_amount":    float(self.txt_refund.text()       or 0),
            "refund_mode":      self.cmb_refund_mode.currentText(),
            "due_date":         self.txt_due_date.text().strip(),
            "remarks":          self.txt_remarks.text().strip(),
            "notes":            self.txt_notes.text().strip(),
            "tax_percent":      cgst_pct + sgst_pct + igst_pct,
            "tax_amount":       cgst_amt + sgst_amt + igst_amt,
        }

    def _preview_invoice(self):
        if not self._validate():
            return
        import os, traceback
        from datetime import date
        from app.constants import INVOICES_PRINT
        from app.printer_helper import _generate_pdf

        preview_data = self._build_invoice_data()
        prefix = AppConfig.invoice_prefix()
        last   = AppConfig.last_invoice_number()
        if self._edit_mode:
            preview_data.setdefault("invoice_number", self._editing_invoice_number)
        else:
            preview_data.setdefault("invoice_number", f"{prefix}-{last + 1:04d} (Preview)")
        # Use the date from the date picker; fall back to today
        preview_data["date"] = preview_data.get("invoice_date") or date.today().strftime("%Y-%m-%d")

        try:
            os.makedirs(INVOICES_PRINT, exist_ok=True)
            preview_path = os.path.join(INVOICES_PRINT, "invoice_preview.pdf")
            _generate_pdf(preview_data, preview_path)
            os.startfile(preview_path)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Preview Error", f"Could not generate preview:\n{e}")

    def _save_invoice(self):
        if not self._validate():
            return
        extra = self._build_invoice_data()

        if self._edit_mode:
            inv = self._do_update(extra)
            if inv is None:
                return
            QMessageBox.information(self, "Updated", f"Invoice {inv['invoice_number']} updated!")
        else:
            inv = create_invoice(
                extra["customer_name"], extra["customer_mobile"],
                extra["customer_address"], list(self._items),
                extra["tax_percent"], notes=extra.get("notes", ""),
                customer_email=extra.get("customer_email", ""),
                extra=extra,
                invoice_date=extra.get("invoice_date", ""),
            )
            QMessageBox.information(self, "Saved", f"Invoice {inv['invoice_number']} saved!")

        self._last_invoice = inv
        self._clear_all()

    def _save_and_print(self):
        if not self._validate():
            return
        extra = self._build_invoice_data()

        if self._edit_mode:
            inv = self._do_update(extra)
            if inv is None:
                return
        else:
            inv = create_invoice(
                extra["customer_name"], extra["customer_mobile"],
                extra["customer_address"], list(self._items),
                extra["tax_percent"], notes=extra.get("notes", ""),
                customer_email=extra.get("customer_email", ""),
                extra=extra,
                invoice_date=extra.get("invoice_date", ""),
            )

        self._last_invoice = inv
        self._clear_all()
        save_invoice_as_pdf(inv, parent=self)

    def _do_update(self, extra: dict):
        """Overwrite the existing invoice record in storage. Returns updated dict or None on failure."""
        from datetime import datetime
        updated = dict(extra)
        updated["invoice_id"]     = self._editing_invoice_id
        updated["invoice_number"] = self._editing_invoice_number
        updated["date"]           = extra.get("invoice_date", "")
        updated["time"]           = datetime.now().strftime("%H:%M:%S")
        updated["customer_email"] = extra.get("customer_email", "")
        if not update_invoice(self._editing_invoice_id, updated):
            QMessageBox.critical(self, "Error", "Failed to update invoice.")
            return None
        return updated

    # ── Quick-Add helpers ─────────────────────────────────────

    def _quick_add_item(self):
        """Compact dialog: create a catalog item and optionally fill it into this invoice."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Quick Add — New Item")
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
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

        # Enter: Name → Code → Purity → Rate → "Save & Add to Invoice"
        _EnterNav([txt_name, txt_code, txt_purity, spn_rate], on_last=lambda: dlg.done(2), parent=dlg)

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
            purity_hint = f" ({purity})" if purity else ""
            code_hint   = f'\n  or code "{code}" is already taken' if code else ""
            QMessageBox.warning(
                self, "Duplicate",
                f'"{name}{purity_hint}" already exists.{code_hint}'
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
        # Remove the Windows "?" help button from the title bar
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
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

        fl = QFormLayout(); fl.setSpacing(8)
        fl.addRow(_lbl("Metal Name *"),  txt_name)
        fl.addRow(_lbl("Purity *"),      txt_purity)
        fl.addRow(_lbl("Rate (₹/g) *"), spn_rate)
        fl.addRow(_lbl("Labour (₹/g)"), spn_labour)
        vl.addLayout(fl)

        # Inline error label — hidden until a validation problem occurs
        err_lbl = QLabel("")
        err_lbl.setWordWrap(True)
        err_lbl.setStyleSheet(
            "color:#e74c3c; font-size:11px; font-weight:600; padding:2px 0;"
        )
        err_lbl.hide()
        vl.addWidget(err_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_save = QPushButton("💾  Save Metal")
        btn_save.setFixedHeight(38)
        btn_save.setDefault(True)   # Enter key triggers Save from any field
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
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_save); btn_row.addWidget(btn_cancel)
        vl.addLayout(btn_row)

        def _try_save():
            name_v   = txt_name.text().strip()
            purity_v = txt_purity.text().strip()
            if not name_v:
                err_lbl.setText("Metal Name is required.")
                err_lbl.show()
                txt_name.setFocus()
                return
            if not purity_v:
                err_lbl.setText("Purity is required.")
                err_lbl.show()
                txt_purity.setFocus()
                return
            ok = _add_metal_rec(name_v, purity_v, spn_rate.value(), spn_labour.value())
            if not ok:
                err_lbl.setText(
                    f'"{name_v} – {purity_v}" already exists. '
                    "Use a different name or purity."
                )
                err_lbl.show()
                return
            dlg.accept()

        btn_save.clicked.connect(_try_save)

        # Enter: Name → Purity → Rate → Labour → Save
        _EnterNav([txt_name, txt_purity, spn_rate, spn_labour], on_last=_try_save, parent=dlg)

        if dlg.exec() != QDialog.Accepted:
            return

        name_v   = txt_name.text().strip()
        purity_v = txt_purity.text().strip()
        QMessageBox.information(
            self, "Saved",
            f'"{name_v} – {purity_v}" added.\n'
            "Go to Settings → Metals to edit it any time."
        )

    def _apply_catalog_item(self, item: dict, rd: dict):
        """Fill purity and rate into a row from a catalog item dict, then focus GWT."""
        purity = item.get('purity', '')
        if purity:
            idx = rd['purity'].findText(purity)
            if idx >= 0:
                rd['purity'].setCurrentIndex(idx)
            else:
                rd['purity'].setCurrentText(purity)
        rate = float(item.get('rate') or 0)
        if rate:
            rd['rate'].setValue(rate)
        self._row_calc(rd)
        self._rebuild_items_from_table()
        # Purity + rate are filled — jump straight to GWT
        QTimer.singleShot(0, lambda: self._focus_and_select(rd['gwt']))

    def _autofill_item_by_name(self, name: str, rd: dict):
        """Called when the user picks a name from the autocomplete dropdown."""
        item = get_item_by_name(name)
        if item:
            self._apply_catalog_item(item, rd)

    def _refresh_item_completers(self):
        """Update the autocomplete list on every item name field in the current table."""
        names = get_catalog_names()
        for rd in self._row_widgets:
            w = rd['name']
            c = QCompleter(names, w)
            c.setCaseSensitivity(Qt.CaseInsensitive)
            c.setFilterMode(Qt.MatchContains)
            w.setCompleter(c)
            c.activated.connect(
                lambda name, _rd=rd: self._autofill_item_by_name(name, _rd)
            )

    def _clear_all(self):
        # Reset edit-mode state
        self._edit_mode = False
        self._editing_invoice_id = ""
        self._selected_customer_id = ""
        self._editing_invoice_number = ""
        self._title_lbl.setText("🧾  New Invoice")
        self._btn_save.setText("💾  Save Invoice")
        self._btn_print.setText("🖨  Save && Print PDF")

        self.dte_invoice.setDate(QDate.currentDate())
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
                  self.txt_upi, self.txt_old_purchase, self.txt_advance,
                  self.txt_roundoff, self.txt_refund, self.txt_due):
            f.clear()
        self.cmb_refund_mode.setCurrentIndex(0)
        self._reset_items_table()
        self.spn_cgst.setValue(1.5)
        self.spn_sgst.setValue(1.5)
        self.spn_igst.setValue(0.0)
        self._recalc_totals()
        self._refresh_inv_number()

    # ── Load saved invoice data ───────────────────────────────

    def load_for_edit(self, inv: dict):
        """Load a saved invoice into the form for editing in-place."""
        self._clear_all()
        self._edit_mode = True
        self._editing_invoice_id     = inv.get("invoice_id", "")
        self._editing_invoice_number = inv.get("invoice_number", "")
        inv_no = self._editing_invoice_number
        self._title_lbl.setText(f"✏️  Edit Invoice  —  {inv_no}")
        self._inv_num_lbl.setText(f"Editing: {inv_no}")
        self._btn_save.setText("💾  Update Invoice")
        self._btn_print.setText("🖨  Update && Print PDF")
        self._load_invoice_data(inv)

    def load_for_duplicate(self, inv: dict):
        """Pre-fill the form from a saved invoice as a starting point for a new invoice."""
        self._clear_all()
        self._load_invoice_data(inv)
        self._title_lbl.setText("🧾  New Invoice  (from copy)")

    def _load_invoice_data(self, inv: dict):
        """Populate all form fields from a saved invoice dict."""
        # Date
        date_str = inv.get("date", "")
        if date_str:
            qd = QDate.fromString(date_str, "yyyy-MM-dd")
            if qd.isValid():
                self.dte_invoice.setDate(qd)

        # Customer — fill fields and try to link to a customer record
        self.txt_cmobile.setText(inv.get("customer_mobile", ""))
        self.txt_cname.setText(inv.get("customer_name", ""))
        self.txt_caddr.setText(inv.get("customer_address", ""))
        self.txt_cemail.setText(inv.get("customer_email", ""))
        self.txt_cust_gst.setText(inv.get("customer_gst", ""))
        self.txt_aadhaar.setText(inv.get("customer_aadhaar", ""))
        self.txt_pan.setText(inv.get("customer_pan", ""))
        mobile = inv.get("customer_mobile", "").strip()
        self._selected_customer_id = ""
        if mobile:
            for c in self._customers_cache:
                if c.get("mobile", "") == mobile:
                    self._selected_customer_id = c.get("customer_id", "")
                    break

        # Items
        self._reset_items_table()
        items = inv.get("items", [])
        for idx, item in enumerate(items):
            if idx > 0:
                self._append_item_row()
            rd = self._row_widgets[idx]

            rd['tag'].setText(item.get("tag", ""))
            rd['name'].setText(item.get("name", ""))
            rd['huid'].setText(item.get("huid", ""))

            purity = item.get("purity", "")
            if purity:
                pi = rd['purity'].findText(purity)
                if pi >= 0:
                    rd['purity'].setCurrentIndex(pi)
                else:
                    rd['purity'].setCurrentText(purity)

            rd['gwt'].blockSignals(True)
            rd['lwt'].blockSignals(True)
            rd['nwt'].blockSignals(True)
            rd['gwt'].setValue(float(item.get("weight",      0)))
            rd['lwt'].setValue(float(item.get("less_weight", 0)))
            rd['nwt'].setValue(float(item.get("nett_weight", 0)))
            rd['gwt'].blockSignals(False)
            rd['lwt'].blockSignals(False)
            rd['nwt'].blockSignals(False)

            rd['qty'].setValue(int(item.get("quantity", 1)))
            rd['rate'].setValue(float(item.get("rate", 0)))

            making_pct = float(item.get("making_pct",    0))
            making_amt = float(item.get("making_charge", 0))
            if making_pct > 0 or making_amt == 0:
                rd['mk_is_pct'][0] = True
                rd['mk_btn'].setText('%')
                rd['mk_btn'].setStyleSheet(
                    "QPushButton{background:#8e44ad;color:white;border-radius:3px;"
                    "font-weight:bold;font-size:10px;border:none;}"
                    "QPushButton:hover{background:#7d3c98;}"
                )
                rd['mk_spn'].setSuffix(' %')
                rd['mk_spn'].setPrefix('')
                rd['mk_spn'].setRange(0, 100)
                rd['mk_spn'].setValue(making_pct)
            else:
                rd['mk_is_pct'][0] = False
                rd['mk_btn'].setText('₹')
                rd['mk_btn'].setStyleSheet(
                    "QPushButton{background:#d35400;color:white;border-radius:3px;"
                    "font-weight:bold;font-size:10px;border:none;}"
                    "QPushButton:hover{background:#b7490a;}"
                )
                rd['mk_spn'].setSuffix('')
                rd['mk_spn'].setPrefix('₹')
                rd['mk_spn'].setRange(0, 9999999)
                rd['mk_spn'].setValue(making_amt)

            rd['other'].setValue(float(item.get("stone_charge", 0)))
            self._row_calc(rd)

        # Tax
        self.spn_cgst.setValue(float(inv.get("cgst_percent", 1.5)))
        self.spn_sgst.setValue(float(inv.get("sgst_percent", 1.5)))
        self.spn_igst.setValue(float(inv.get("igst_percent", 0.0)))

        self._rebuild_items_from_table()

        # Payment fields — restore after recalc (recalc may auto-set refund/due)
        def _set_money(field, key):
            val = float(inv.get(key, 0) or 0)
            field.setText(f"{val:.2f}" if val else "")

        _set_money(self.txt_cash,          "cash_paid")
        _set_money(self.txt_card,          "card_paid")
        _set_money(self.txt_cheque,        "cheque_paid")
        _set_money(self.txt_upi,           "upi_paid")
        _set_money(self.txt_old_purchase,  "old_purchase")
        _set_money(self.txt_advance,       "advance_paid")
        _set_money(self.txt_roundoff,      "round_off")

        self.txt_card_details.setText(inv.get("card_details", ""))
        self.txt_cheque_details.setText(inv.get("cheque_details", ""))

        # Trigger recalc after restoring payment fields so due/refund updates
        self._recalc_due()

        # Override auto-calculated refund/due with saved values
        refund_val = float(inv.get("refund_amount", 0) or 0)
        due_val    = float(inv.get("due_amount",    0) or 0)
        if refund_val:
            self.txt_refund.blockSignals(True)
            self.txt_refund.setText(f"{refund_val:.2f}")
            self.txt_refund.blockSignals(False)
        if due_val:
            self.txt_due.setText(f"{due_val:.2f}")

        refund_mode = inv.get("refund_mode", "Cash")
        idx = self.cmb_refund_mode.findText(refund_mode)
        if idx >= 0:
            self.cmb_refund_mode.setCurrentIndex(idx)

        self.txt_due_date.setText(inv.get("due_date", ""))
        self.txt_remarks.setText(inv.get("remarks", ""))
        self.txt_notes.setText(inv.get("notes", ""))

    def refresh(self):
        self._refresh_inv_number()

        # Refresh customer cache + completers so new customers show up
        self._customers_cache = get_all_customers()
        self._rebuild_customer_completers()