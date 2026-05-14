# ============================================================
# ui/karigar_page.py — Karigar Ledger (TAKE / GIVE)
# ============================================================
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QScrollArea, QHeaderView, QAbstractItemView, QComboBox,
    QGridLayout, QMessageBox, QDateEdit, QGroupBox, QSplitter,
    QStyledItemDelegate, QCompleter, QStackedWidget, QSizePolicy,
    QToolButton,
)
from PyQt5.QtCore import Qt, QDate, QEvent, QTimer
from PyQt5.QtGui import QFont, QColor

from services.karigar_service import (
    get_all_transactions, add_transaction, get_next_memo_no,
    get_karigar_summary, get_all_karigar_summaries,
    get_profile_by_name, get_profile_names, add_or_update_profile,
)

# ── Styles ────────────────────────────────────────────────────
_GRP = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#2c3e50;"
    "border:1px solid #dde6ed;border-radius:6px;margin-top:10px;padding-top:6px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 5px;background:white;}"
)
_INP = (
    "QLineEdit{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
    "font-size:12px;background:white;min-height:28px;max-height:28px;}"
    "QLineEdit:focus{border:2px solid #3498db;background:#eaf6fd;}"
)
_RO = (
    "QLineEdit{border:1px solid #b2c8d0;border-radius:4px;padding:0 7px;"
    "font-size:12px;background:#f0f7fb;color:#1a6680;font-weight:bold;"
    "min-height:28px;max-height:28px;}"
)
_DTE = (
    "QDateEdit{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
    "font-size:12px;background:white;min-height:28px;max-height:28px;}"
    "QDateEdit::drop-down{border:none;}"
)
_CMB = (
    "QComboBox{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
    "font-size:12px;background:white;min-height:28px;max-height:28px;}"
    "QComboBox:focus{border:2px solid #3498db;}"
    "QComboBox::drop-down{border:none;width:16px;}"
)

class _ClickDateEdit(QDateEdit):
    """QDateEdit that opens the calendar popup on any mouse click."""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.calendarPopup():
            btn = self.findChild(QToolButton)
            if btn:
                btn.click()

_TAKE_SKIP = {6}      # Fine Gold only — read-only, skipped by Enter
_TAKE_COLS = ["Description", "Pc", "G.Wt (g)", "Less Wt (g)",
              "Net Wt (g)", "Tounch", "Fine Gold (g)"]


# ── Helpers ───────────────────────────────────────────────────
def _lbl(text, bold=False, color="#444"):
    l = QLabel(text)
    s = f"color:{color};font-size:11px;"
    if bold: s += "font-weight:bold;"
    l.setStyleSheet(s)
    return l

def _inp(ph=""):
    e = QLineEdit(); e.setPlaceholderText(ph); e.setStyleSheet(_INP)
    return e

def _ro(text="0.000"):
    e = QLineEdit(text); e.setReadOnly(True); e.setStyleSheet(_RO)
    e.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return e

def _amt_inp(ph="0.000"):
    e = QLineEdit(); e.setPlaceholderText(ph)
    e.setStyleSheet(_INP)
    e.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return e

def _dte(date=None):
    d = _ClickDateEdit(date or QDate.currentDate())
    d.setCalendarPopup(True); d.setDisplayFormat("dd-MM-yyyy")
    d.setStyleSheet(_DTE)
    return d

_HOVER_MAP = {
    "#27ae60": "#1e8449",
    "#2980b9": "#1a6895",
    "#7f8c8d": "#626567",
    "#8e44ad": "#7d3c98",
    "#c0392b": "#a93226",
}

def _btn(text, color="#2980b9", h=30):
    hover = _HOVER_MAP.get(color, "#555")
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:white;border:none;"
        f"border-radius:4px;font-size:11px;font-weight:bold;padding:0 14px;}}"
        f"QPushButton:hover{{background:{hover};}}"
    )
    return b

def _fv(v):
    try: return float(v) if v else 0.0
    except: return 0.0


# ── Take Table ─────────────────────────────────────────────────
class _TakeTable(QTableWidget):
    """Item table for TAKE entries — Enter navigates right, wraps to new row.
    When Enter is pressed at the last cell of an already-empty last row,
    calls on_last_empty() instead of adding yet another blank row.
    """

    on_last_empty = None   # set by KarigarPage after Save button is created

    def moveCursor(self, action, mods):
        if action == QAbstractItemView.MoveNext:
            row, col = self.currentRow(), self.currentColumn()
            ncol = col + 1
            while ncol < self.columnCount() and ncol in _TAKE_SKIP:
                ncol += 1
            if ncol < self.columnCount():
                return self.model().index(row, ncol)

            # End of row — would wrap to next
            nrow = row + 1
            if nrow >= self.rowCount():
                # Need a new row: only add one if current last row has data
                if self._is_row_empty(row):
                    if self.on_last_empty:
                        QTimer.singleShot(0, self.on_last_empty)
                    return self.currentIndex()   # stay put, focus goes to Save
                self._append_row()
            return self.model().index(nrow, 0)
        return super().moveCursor(action, mods)

    def _is_row_empty(self, row: int) -> bool:
        for c in range(self.columnCount()):
            if c in _TAKE_SKIP:
                continue
            item = self.item(row, c)
            if item and item.text().strip():
                return False
        return True

    def _append_row(self):
        r = self.rowCount(); self.insertRow(r)
        for c in range(self.columnCount()):
            cell = QTableWidgetItem("")
            if c in _TAKE_SKIP:
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                cell.setBackground(QColor("#e8f4f8"))
            self.setItem(r, c, cell)


class _TakeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() in _TAKE_SKIP:
            return None
        return super().createEditor(parent, option, index)

    def updateEditorGeometry(self, editor, option, index):
        # Fill the entire cell rect — no inset margins so text is never clipped
        editor.setGeometry(option.rect)

    def eventFilter(self, editor, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.commitData.emit(editor)
            self.closeEditor.emit(editor, QStyledItemDelegate.EditNextItem)
            return True
        return super().eventFilter(editor, event)


# ============================================================
class KarigarPage(QWidget):

    def __init__(self):
        super().__init__()
        self._mode = "TAKE"
        self._current_karigar = ""
        self._all_transactions: list = []
        self._build_ui()

    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([480, 620])
        root.addWidget(splitter)

    # ── LEFT PANEL ────────────────────────────────────────
    def _build_left(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumWidth(440)

        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(16, 12, 12, 12)
        vl.setSpacing(8)
        scroll.setWidget(w)

        # Title
        title = QLabel("Vendor Ledger Entry")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title.setStyleSheet("color:#2c3e50;")
        vl.addWidget(title)

        # Karigar info
        vl.addWidget(self._build_karigar_section())

        # Mode toggle
        toggle = QHBoxLayout(); toggle.setSpacing(0)
        self._btn_take = QPushButton("📥  TAKE from Vendor")
        self._btn_give = QPushButton("📤  GIVE to Vendor")
        for b in (self._btn_take, self._btn_give):
            b.setFixedHeight(34)
            b.setCheckable(False)
        self._btn_take.clicked.connect(lambda: self._set_mode("TAKE"))
        self._btn_give.clicked.connect(lambda: self._set_mode("GIVE"))
        toggle.addWidget(self._btn_take)
        toggle.addWidget(self._btn_give)
        vl.addLayout(toggle)

        # Stacked: TAKE form / GIVE form
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_take_form())   # index 0
        self._stack.addWidget(self._build_give_form())   # index 1
        vl.addWidget(self._stack, 1)

        # Save button — sits between form and summary bar
        self._btn_save = _btn("💾  Save Entry", "#27ae60", 40)
        self._btn_save.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._btn_save.clicked.connect(self._save)
        vl.addWidget(self._btn_save)

        # Summary bar (Fine Gold Taken / Given / Dues) — pinned at the bottom
        vl.addWidget(self._build_summary_bar())

        # Empty last row Enter / Give remarks Enter → save directly
        self.tbl_take.on_last_empty = self._save
        self.give_remarks.returnPressed.connect(self._save)

        self._set_mode("TAKE")
        return scroll

    def _build_karigar_section(self) -> QGroupBox:
        grp = QGroupBox("Vendor Details"); grp.setStyleSheet(_GRP)
        g = QGridLayout(grp)
        g.setSpacing(6); g.setContentsMargins(12, 14, 12, 10)
        g.setColumnStretch(1, 1); g.setColumnStretch(3, 1)

        self.fld_name   = _inp("Vendor name or code…")
        self.fld_mobile = _inp("Mobile")
        self.fld_email  = _inp("Email")
        self.fld_pan    = _inp("PAN")
        self.fld_memo   = _ro("KAR-0001")
        self.dte_date   = _dte()

        self.fld_name.setStyleSheet(
            "QLineEdit{border:1px solid #f39c12;border-radius:4px;padding:0 7px;"
            "font-size:12px;font-weight:bold;background:white;min-height:28px;max-height:28px;}"
            "QLineEdit:focus{border:2px solid #e67e22;background:#fff9f0;}"
        )

        g.addWidget(_lbl("Name *:"),    0, 0); g.addWidget(self.fld_name,   0, 1)
        g.addWidget(_lbl("Date *:"),    0, 2); g.addWidget(self.dte_date,    0, 3)
        g.addWidget(_lbl("Mobile:"),    1, 0); g.addWidget(self.fld_mobile,  1, 1)
        g.addWidget(_lbl("Email:"),     1, 2); g.addWidget(self.fld_email,   1, 3)
        g.addWidget(_lbl("PAN:"),       2, 0); g.addWidget(self.fld_pan,     2, 1)
        g.addWidget(_lbl("Memo No:"),   2, 2); g.addWidget(self.fld_memo,    2, 3)

        self._setup_karigar_completer()

        # Enter navigation: Name → Mobile → Email → PAN → Date → form
        self.fld_name.returnPressed.connect(self._on_name_enter)
        self.fld_mobile.returnPressed.connect(self.fld_email.setFocus)
        self.fld_email.returnPressed.connect(self.fld_pan.setFocus)
        self.fld_pan.returnPressed.connect(self.dte_date.setFocus)
        self.dte_date.installEventFilter(self)   # Enter on date → into form
        self.fld_name.textChanged.connect(self._on_karigar_text_changed)

        return grp

    def _build_take_form(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 4, 0, 0); vl.setSpacing(6)

        grp = QGroupBox("Items Received  —  Enter moves right; auto-wraps to new row")
        grp.setStyleSheet(_GRP)
        gl = QVBoxLayout(grp); gl.setContentsMargins(8, 12, 8, 8)

        self.tbl_take = _TakeTable(0, len(_TAKE_COLS))
        self.tbl_take.setHorizontalHeaderLabels(_TAKE_COLS)

        hdr = self.tbl_take.horizontalHeader()
        hdr.setFixedHeight(40)
        hdr.setDefaultAlignment(Qt.AlignCenter)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        _fixed = {1: 46, 2: 88, 3: 88, 4: 88, 5: 78, 6: 100}
        for c, width in _fixed.items():
            self.tbl_take.setColumnWidth(c, width)
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        hdr.setStyleSheet(
            "QHeaderView::section{"
            "background:#2c3e50;color:white;font-size:11px;font-weight:bold;"
            "padding:6px 4px;border:none;"
            "border-right:1px solid #3d5166;border-bottom:2px solid #f39c12;}"
        )

        self.tbl_take.setStyleSheet(
            "QTableWidget{font-size:12px;gridline-color:#dde6ed;}"
            "QTableWidget::item{padding:0px;}"
            "QTableWidget::item:selected{background:#d5e8f7;color:#1a2a3a;}"
            "QTableWidget::item:focus{background:#fff3cd;}"
        )
        self.tbl_take.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.tbl_take.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tbl_take.setAlternatingRowColors(True)
        self.tbl_take.verticalHeader().setVisible(False)
        self.tbl_take.verticalHeader().setDefaultSectionSize(36)
        self.tbl_take.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tbl_take.setMinimumHeight(200)
        self.tbl_take.setItemDelegate(_TakeDelegate(self.tbl_take))
        self.tbl_take.itemChanged.connect(self._on_take_cell_changed)
        gl.addWidget(self.tbl_take)

        self.tbl_take._append_row()
        vl.addWidget(grp)

        # Standalone dues label — updates as cells are filled
        self.lbl_take_dues = QLabel("Outstanding Dues (with this entry): 0.000 g")
        self.lbl_take_dues.setStyleSheet(
            "font-size:12px;font-weight:bold;color:#c0392b;"
            "padding:4px 8px;background:#fdf2f0;border-radius:4px;"
            "border:1px solid #e8c2bb;"
        )
        self.lbl_take_dues.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vl.addWidget(self.lbl_take_dues)

        return w

    def _build_give_form(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 4, 0, 0); vl.setSpacing(8)

        # ── Gold section ──────────────────────────────────
        grp_g = QGroupBox("Gold Given (leave blank if giving only cash)")
        grp_g.setStyleSheet(_GRP)
        gg = QGridLayout(grp_g)
        gg.setSpacing(6); gg.setContentsMargins(12, 14, 12, 10)
        gg.setColumnStretch(1, 1); gg.setColumnStretch(3, 1)

        self.give_g_gwt    = _amt_inp("0.000")
        self.give_g_lwt    = _amt_inp("0.000")
        self.give_g_nwt    = _amt_inp("0.000")
        self.give_g_tounch = _amt_inp("0.000")
        self.give_g_fg     = _ro("0.000")

        gg.addWidget(_lbl("G.Wt (g):"),     0, 0); gg.addWidget(self.give_g_gwt,    0, 1)
        gg.addWidget(_lbl("Less Wt (g):"),  0, 2); gg.addWidget(self.give_g_lwt,    0, 3)
        gg.addWidget(_lbl("Net Wt (g):"),   1, 0); gg.addWidget(self.give_g_nwt,    1, 1)
        gg.addWidget(_lbl("Tounch (%):"),   1, 2); gg.addWidget(self.give_g_tounch, 1, 3)
        gg.addWidget(_lbl("Fine Gold (g):"),2, 0); gg.addWidget(self.give_g_fg,     2, 1, 1, 3)

        for fld in (self.give_g_gwt, self.give_g_lwt):
            fld.textChanged.connect(self._recalc_give_gold_nwt)
        for fld in (self.give_g_nwt, self.give_g_tounch):
            fld.textChanged.connect(self._recalc_give_gold_fg)
        vl.addWidget(grp_g)

        # ── Cash section ──────────────────────────────────
        grp_c = QGroupBox("Cash / RTGS Given (leave blank if giving only gold)")
        grp_c.setStyleSheet(_GRP)
        gc = QGridLayout(grp_c)
        gc.setSpacing(6); gc.setContentsMargins(12, 14, 12, 10)
        gc.setColumnStretch(1, 1); gc.setColumnStretch(3, 1)

        self.give_c_cash   = _amt_inp("0.00")
        self.give_c_rate   = _amt_inp("Rate per 10g ₹")
        self.give_c_fg     = _ro("0.000")

        gc.addWidget(_lbl("Cash / RTGS (₹):"),  0, 0); gc.addWidget(self.give_c_cash, 0, 1)
        gc.addWidget(_lbl("Rate / 10g (₹):"),   0, 2); gc.addWidget(self.give_c_rate, 0, 3)
        gc.addWidget(_lbl("Fine Gold (g):"),     1, 0); gc.addWidget(self.give_c_fg,   1, 1, 1, 3)

        for fld in (self.give_c_cash, self.give_c_rate):
            fld.textChanged.connect(self._recalc_give_cash_fg)
        vl.addWidget(grp_c)

        # ── Totals ────────────────────────────────────────
        grp_t = QGroupBox("Give Summary")
        grp_t.setStyleSheet(_GRP)
        gt = QGridLayout(grp_t)
        gt.setSpacing(6); gt.setContentsMargins(12, 14, 12, 10)
        gt.setColumnStretch(1, 1); gt.setColumnStretch(3, 1)

        self.give_total_fg  = _ro("0.000")
        self.give_total_fg.setStyleSheet(self.give_total_fg.styleSheet() + "font-size:13px;")
        self.give_remarks   = _inp("Remarks (optional)")

        gt.addWidget(_lbl("Total Fine Gold Given (g):", bold=True), 0, 0)
        gt.addWidget(self.give_total_fg,  0, 1)
        gt.addWidget(_lbl("Remarks:"), 1, 0)
        gt.addWidget(self.give_remarks, 1, 1, 1, 3)
        vl.addWidget(grp_t)

        # Enter navigation for give form fields
        _give_nav = [
            self.give_g_gwt, self.give_g_lwt, self.give_g_nwt, self.give_g_tounch,
            self.give_c_cash, self.give_c_rate, self.give_remarks,
        ]
        for i, f in enumerate(_give_nav[:-1]):
            f.returnPressed.connect(_give_nav[i+1].setFocus)

        vl.addStretch()
        return w

    def _build_summary_bar(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame{background:#1a3a5c;border-radius:6px;padding:2px;}"
        )
        h = QHBoxLayout(f); h.setContentsMargins(16, 8, 16, 8); h.setSpacing(0)

        def _card(label, attr, color="#7fb3d3"):
            v = QVBoxLayout(); v.setSpacing(1)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{color};font-size:10px;font-weight:bold;background:transparent;")
            val = QLabel("0.000 g")
            val.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;")
            val.setAlignment(Qt.AlignCenter)
            v.addWidget(lbl); v.addWidget(val)
            setattr(self, attr, val)
            return v

        h.addLayout(_card("FINE GOLD TAKEN", "lbl_sum_take", "#82e0aa"))
        sep1 = QFrame(); sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("QFrame{color:#345;background:#345;}")
        h.addWidget(sep1)
        h.addLayout(_card("FINE GOLD GIVEN", "lbl_sum_give", "#aed6f1"))
        sep2 = QFrame(); sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("QFrame{color:#345;background:#345;}")
        h.addWidget(sep2)
        h.addLayout(_card("OUTSTANDING DUES", "lbl_sum_dues", "#f1948a"))

        return f

    # ── RIGHT PANEL ───────────────────────────────────────
    def _build_right(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:#f8f9fa;")
        vl = QVBoxLayout(w); vl.setContentsMargins(10, 12, 14, 12); vl.setSpacing(8)

        hd = QHBoxLayout()
        self.lbl_right_title = QLabel("Transaction History")
        self.lbl_right_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.lbl_right_title.setStyleSheet("color:#2c3e50;background:transparent;")
        hd.addWidget(self.lbl_right_title); hd.addStretch()
        vl.addLayout(hd)

        # Filter bar
        fb = QHBoxLayout(); fb.setSpacing(6)
        fb.addWidget(_lbl("From:"))
        self.dt_from = _ClickDateEdit(QDate.currentDate().addMonths(-12))
        self.dt_from.setCalendarPopup(True); self.dt_from.setDisplayFormat("dd-MM-yyyy")
        self.dt_from.setFixedHeight(28); self.dt_from.setStyleSheet(_DTE)
        self.dt_from.dateChanged.connect(self._reload_right)
        fb.addWidget(self.dt_from)

        fb.addWidget(_lbl("To:"))
        self.dt_to = _ClickDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True); self.dt_to.setDisplayFormat("dd-MM-yyyy")
        self.dt_to.setFixedHeight(28); self.dt_to.setStyleSheet(_DTE)
        self.dt_to.dateChanged.connect(self._reload_right)
        fb.addWidget(self.dt_to)

        fb.addWidget(_lbl("Type:"))
        self.cmb_tx_type = QComboBox()
        self.cmb_tx_type.addItems(["All", "TAKE", "GIVE"])
        self.cmb_tx_type.setFixedHeight(28); self.cmb_tx_type.setStyleSheet(_CMB)
        self.cmb_tx_type.currentIndexChanged.connect(self._reload_right)
        fb.addWidget(self.cmb_tx_type)

        btn_all = _btn("All Dates", "#7f8c8d", 28)
        btn_all.clicked.connect(self._show_all_dates)
        fb.addWidget(btn_all)
        fb.addStretch()
        vl.addLayout(fb)

        # Transaction table
        _TC = ["Date", "Memo", "Type", "Description", "Net Wt (g)", "Tounch", "Fine Gold (g)", "Cash (₹)"]
        self.tbl_tx = QTableWidget(0, len(_TC))
        self.tbl_tx.setHorizontalHeaderLabels(_TC)
        hdr = self.tbl_tx.horizontalHeader()
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr.setMinimumSectionSize(52)
        for c in range(len(_TC)):
            if c != 3:
                hdr.setSectionResizeMode(c, QHeaderView.Interactive)
        _init_w = {0: 86, 1: 72, 2: 52, 4: 76, 5: 62, 6: 88, 7: 80}
        for c, cw in _init_w.items():
            self.tbl_tx.setColumnWidth(c, cw)
        self.tbl_tx.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_tx.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_tx.setAlternatingRowColors(True)
        self.tbl_tx.verticalHeader().setVisible(False)
        self.tbl_tx.verticalHeader().setDefaultSectionSize(30)
        self.tbl_tx.setMinimumHeight(300)
        vl.addWidget(self.tbl_tx, 1)

        # Footer summary
        sf = QFrame()
        sf.setStyleSheet(
            "QFrame{background:white;border:1px solid #dde6ed;border-radius:5px;}"
        )
        sl = QHBoxLayout(sf); sl.setContentsMargins(14, 8, 14, 8); sl.setSpacing(20)
        self.lbl_r_txcount  = QLabel("Txns: 0")
        self.lbl_r_take_fg  = QLabel("Fine Taken: 0.000 g")
        self.lbl_r_give_fg  = QLabel("Fine Given: 0.000 g")
        self.lbl_r_dues     = QLabel("Dues: 0.000 g")
        for lbl in (self.lbl_r_txcount, self.lbl_r_take_fg, self.lbl_r_give_fg, self.lbl_r_dues):
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("background:transparent; color:#2c3e50;")
            sl.addWidget(lbl)
        sl.addStretch()
        vl.addWidget(sf)
        return w

    # ── Mode toggle ───────────────────────────────────────
    def _set_mode(self, mode: str):
        self._mode = mode
        active_style = (
            "QPushButton{background:#2c3e50;color:white;border:none;"
            "font-size:12px;font-weight:bold;min-height:34px;}"
        )
        inactive_style = (
            "QPushButton{background:#dde6ed;color:#555;border:none;"
            "font-size:12px;min-height:34px;}"
            "QPushButton:hover{background:#c8d6df;}"
        )
        if mode == "TAKE":
            self._btn_take.setStyleSheet(active_style + "border-radius:6px 0 0 6px;")
            self._btn_give.setStyleSheet(inactive_style + "border-radius:0 6px 6px 0;")
            self._stack.setCurrentIndex(0)
        else:
            self._btn_take.setStyleSheet(inactive_style + "border-radius:6px 0 0 6px;")
            self._btn_give.setStyleSheet(active_style + "border-radius:0 6px 6px 0;")
            self._stack.setCurrentIndex(1)

    # ── Karigar autocomplete ───────────────────────────────
    def _setup_karigar_completer(self):
        names = get_profile_names()
        c = QCompleter(names, self.fld_name)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setFilterMode(Qt.MatchContains)
        self.fld_name.setCompleter(c)
        try: c.activated.disconnect()
        except: pass
        c.activated.connect(self._autofill_karigar)

    def _on_name_enter(self):
        """Autofill karigar details then move focus to Mobile."""
        self._autofill_karigar(self.fld_name.text().strip())
        self.fld_mobile.setFocus()

    def _autofill_karigar(self, name: str):
        if not name: return
        p = get_profile_by_name(name)
        if not p: return
        for fld, key in [(self.fld_mobile, "mobile"), (self.fld_email, "email"), (self.fld_pan, "pan")]:
            v = p.get(key, "")
            if v:
                fld.blockSignals(True); fld.setText(v); fld.blockSignals(False)

    def eventFilter(self, obj, event):
        """Forward Enter on QDateEdit into the active entry form."""
        if obj is self.dte_date and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._focus_form_start()
                return True
        return super().eventFilter(obj, event)

    def _focus_form_start(self):
        """Move focus to the first editable field of the active TAKE/GIVE form."""
        if self._mode == "TAKE":
            if self.tbl_take.rowCount() == 0:
                self.tbl_take._append_row()
            self.tbl_take.setCurrentCell(0, 0)
            self.tbl_take.setFocus()
            self.tbl_take.edit(self.tbl_take.currentIndex())
        else:
            self.give_g_gwt.setFocus()

    def _on_karigar_text_changed(self, text: str):
        # Delay reload so completer can finish
        QTimer.singleShot(300, lambda: self._update_karigar_context(text.strip()))

    def _update_karigar_context(self, name: str):
        if name == self._current_karigar: return
        self._current_karigar = name
        self._reload_right()
        self._update_summary_bar()

    # ── Take table auto-calc ──────────────────────────────
    def _on_take_cell_changed(self, item):
        col = item.column()
        if col not in (2, 3, 4, 5): return
        row = item.row()
        self.tbl_take.blockSignals(True)
        try:
            def _v(c):
                it = self.tbl_take.item(row, c)
                return _fv(it.text() if it else "")

            if col in (2, 3):
                # G.Wt or Less Wt changed → update Net Wt
                nwt = max(0.0, round(_v(2) - _v(3), 3))
                it = self.tbl_take.item(row, 4)
                if it: it.setText(f"{nwt:.3f}")

            # Recalc Fine Gold from current Net Wt and Tounch
            nwt = _v(4); tounch = _v(5)
            fg = round(nwt * tounch / 100.0, 3)
            it6 = self.tbl_take.item(row, 6)
            if it6:
                it6.setText(f"{fg:.3f}")
                it6.setForeground(QColor("#1a6680"))

            # Update standalone dues label
            self._refresh_take_dues_label()
        finally:
            self.tbl_take.blockSignals(False)

    def _base_dues(self) -> float:
        name = self.fld_name.text().strip()
        if not name: return 0.0
        s = get_karigar_summary(name)
        return s.get("dues_fg", 0.0)

    def _refresh_take_dues_label(self):
        if not hasattr(self, "lbl_take_dues"):
            return
        total_new_fg = sum(
            _fv((self.tbl_take.item(r, 6).text() if self.tbl_take.item(r, 6) else ""))
            for r in range(self.tbl_take.rowCount())
        )
        dues = round(self._base_dues() + total_new_fg, 3)
        self.lbl_take_dues.setText(f"Outstanding Dues (with this entry): {dues:.3f} g")
        color = "#c0392b" if dues > 0 else "#27ae60"
        self.lbl_take_dues.setStyleSheet(
            f"font-size:12px;font-weight:bold;color:{color};"
            "padding:4px 8px;border-radius:4px;"
            f"background:{'#fdf2f0' if dues > 0 else '#eafaf1'};"
            f"border:1px solid {'#e8c2bb' if dues > 0 else '#a9dfbf'};"
        )

    # ── Give form auto-calc ───────────────────────────────
    def _recalc_give_gold_nwt(self):
        gwt = _fv(self.give_g_gwt.text())
        lwt = _fv(self.give_g_lwt.text())
        nwt = max(0.0, round(gwt - lwt, 3))
        self.give_g_nwt.blockSignals(True)
        self.give_g_nwt.setText(f"{nwt:.3f}")
        self.give_g_nwt.blockSignals(False)
        self._recalc_give_gold_fg()

    def _recalc_give_gold_fg(self):
        nwt    = _fv(self.give_g_nwt.text())
        tounch = _fv(self.give_g_tounch.text())
        fg = round(nwt * tounch / 100.0, 3)
        self.give_g_fg.setText(f"{fg:.3f}")
        self._recalc_give_total()

    def _recalc_give_cash_fg(self):
        cash = _fv(self.give_c_cash.text())
        rate = _fv(self.give_c_rate.text())
        fg = round((cash * 10.0 / rate), 3) if rate > 0 else 0.0
        self.give_c_fg.setText(f"{fg:.3f}")
        self._recalc_give_total()

    def _recalc_give_total(self):
        fg_gold = _fv(self.give_g_fg.text())
        fg_cash = _fv(self.give_c_fg.text())
        total   = round(fg_gold + fg_cash, 3)
        self.give_total_fg.setText(f"{total:.3f}")

    # ── Summary bar ───────────────────────────────────────
    def _update_summary_bar(self):
        name = self.fld_name.text().strip()
        s = get_karigar_summary(name) if name else {"total_take_fg":0,"total_give_fg":0,"dues_fg":0}
        self.lbl_sum_take.setText(f"{s['total_take_fg']:.3f} g")
        self.lbl_sum_give.setText(f"{s['total_give_fg']:.3f} g")
        dues = s["dues_fg"]
        self.lbl_sum_dues.setText(f"{dues:.3f} g")
        color = "#f1948a" if dues > 0 else "#82e0aa"
        self.lbl_sum_dues.setStyleSheet(f"color:{color};font-size:13px;font-weight:bold;background:transparent;")

    # ── Save ─────────────────────────────────────────────
    def _save(self):
        name = self.fld_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Vendor name is required.")
            self.fld_name.setFocus(); return

        # Save or update karigar profile
        add_or_update_profile(
            name,
            mobile  = self.fld_mobile.text().strip(),
            email   = self.fld_email.text().strip(),
            pan     = self.fld_pan.text().strip(),
        )

        if self._mode == "TAKE":
            self._save_take(name)
        else:
            self._save_give(name)

    def _save_take(self, name: str):
        items = []
        total_fg = 0.0
        for r in range(self.tbl_take.rowCount()):
            def _t(c, row=r):
                it = self.tbl_take.item(row, c)
                return (it.text() if it else "").strip()
            desc = _t(0)
            if not desc: continue
            fg = _fv(_t(6))
            total_fg += fg
            items.append({
                "description": desc,
                "pc":          int(_fv(_t(1))),
                "gross_wt":    _fv(_t(2)),
                "less_wt":     _fv(_t(3)),
                "net_wt":      _fv(_t(4)),
                "tounch":      _fv(_t(5)),
                "fine_gold":   fg,
            })
        if not items:
            QMessageBox.warning(self, "Validation", "Add at least one item.")
            return

        memo_no = self.fld_memo.text().strip()
        existing_memos = {t.get("memo_no", "") for t in self._all_transactions}
        if memo_no in existing_memos:
            QMessageBox.warning(self, "Duplicate Memo",
                f"Memo number '{memo_no}' already exists. Please use a unique memo number.")
            return

        tx = {
            "tx_type":         "TAKE",
            "memo_no":         memo_no,
            "karigar_name":    name,
            "karigar_mobile":  self.fld_mobile.text().strip(),
            "date":            self.dte_date.date().toString("yyyy-MM-dd"),
            "items":           items,
            "total_fine_gold": round(total_fg, 3),
        }
        add_transaction(tx)
        QMessageBox.information(self, "Saved", f"TAKE entry {tx['memo_no']} saved.\nFine Gold: {total_fg:.3f} g")
        self._reset_take()
        self.refresh()

    def _save_give(self, name: str):
        fg_gold = _fv(self.give_g_fg.text())
        fg_cash = _fv(self.give_c_fg.text())
        total_fg = round(fg_gold + fg_cash, 3)

        if total_fg <= 0:
            QMessageBox.warning(self, "Validation",
                "Enter gold details or cash amount (with rate) to record a GIVE entry.")
            return

        memo_no = self.fld_memo.text().strip()
        existing_memos = {t.get("memo_no", "") for t in self._all_transactions}
        if memo_no in existing_memos:
            QMessageBox.warning(self, "Duplicate Memo",
                f"Memo number '{memo_no}' already exists. Please use a unique memo number.")
            return

        tx = {
            "tx_type":              "GIVE",
            "memo_no":              memo_no,
            "karigar_name":         name,
            "karigar_mobile":       self.fld_mobile.text().strip(),
            "date":                 self.dte_date.date().toString("yyyy-MM-dd"),
            "give_gold_gross_wt":   _fv(self.give_g_gwt.text()),
            "give_gold_less_wt":    _fv(self.give_g_lwt.text()),
            "give_gold_net_wt":     _fv(self.give_g_nwt.text()),
            "give_gold_tounch":     _fv(self.give_g_tounch.text()),
            "give_gold_fine":       round(fg_gold, 3),
            "give_cash":            _fv(self.give_c_cash.text()),
            "give_rate_10g":        _fv(self.give_c_rate.text()),
            "give_cash_fine":       round(fg_cash, 3),
            "total_fine_gold":      total_fg,
            "remarks":              self.give_remarks.text().strip(),
        }
        add_transaction(tx)
        QMessageBox.information(self, "Saved",
            f"GIVE entry {tx['memo_no']} saved.\nFine Gold Given: {total_fg:.3f} g")
        self._reset_give()
        self.refresh()

    # ── Reset ─────────────────────────────────────────────
    def _reset_take(self):
        self.tbl_take.setRowCount(0)
        self.tbl_take._append_row()
        self.dte_date.setDate(QDate.currentDate())

    def _reset_give(self):
        for fld in (self.give_g_gwt, self.give_g_lwt, self.give_g_nwt,
                    self.give_g_tounch, self.give_c_cash, self.give_c_rate):
            fld.clear()
        for fld in (self.give_g_fg, self.give_c_fg, self.give_total_fg):
            fld.setText("0.000")
        self.give_remarks.clear()
        self.dte_date.setDate(QDate.currentDate())

    # ── Right panel reload ────────────────────────────────
    def _show_all_dates(self):
        self.dt_from.setDate(QDate(2000, 1, 1))
        self.dt_to.setDate(QDate.currentDate())
        self._reload_right()

    def _reload_right(self):
        name   = self._current_karigar
        d_from = self.dt_from.date().toString("yyyy-MM-dd")
        d_to   = self.dt_to.date().toString("yyyy-MM-dd")
        tf     = self.cmb_tx_type.currentText()

        if name:
            self.lbl_right_title.setText(f"Transactions — {name}")
        else:
            self.lbl_right_title.setText("Transaction History  (select a vendor)")

        txs = [
            t for t in self._all_transactions
            if (not name or t.get("karigar_name","").strip() == name)
            and d_from <= t.get("date","") <= d_to
            and (tf == "All" or t.get("tx_type","TAKE") == tf)
        ]
        # Sort oldest first for running dues
        txs_sorted = sorted(txs, key=lambda x: x.get("date",""))

        self.tbl_tx.setRowCount(0)
        running = 0.0
        t_take_fg = t_give_fg = 0.0

        for tx in txs_sorted:
            r = self.tbl_tx.rowCount()
            self.tbl_tx.insertRow(r)
            tx_type = tx.get("tx_type", "TAKE")
            fg = float(tx.get("total_fine_gold", 0) or 0)
            cash = float(tx.get("total_payment", tx.get("give_cash", 0)) or 0)

            if tx_type == "TAKE":
                running += fg
                t_take_fg += fg
                desc = "; ".join(
                    f"{it.get('description','?')} x{it.get('pc',1)}"
                    for it in tx.get("items", [])
                )
                nwt   = sum(float(it.get("net_wt",0)) for it in tx.get("items",[]))
                touch = ", ".join(
                    f"{it.get('tounch',0):.1f}%"
                    for it in tx.get("items",[])
                )
                cash_str = "—"
                bg = QColor("#fde8e8")   # light red — TAKE
                fg_color = QColor("#7b1a1a")
            else:  # GIVE
                running -= fg
                t_give_fg += fg
                parts = []
                if tx.get("give_gold_net_wt", 0): parts.append("Gold")
                if tx.get("give_cash", 0):         parts.append("Cash")
                desc = " + ".join(parts) + " given" if parts else "Given"
                nwt   = float(tx.get("give_gold_net_wt", 0) or 0)
                touch = f"{tx.get('give_gold_tounch',0):.1f}%" if tx.get("give_gold_net_wt") else "—"
                cash_str = f"{cash:,.2f}"
                bg = QColor("#e8f8ee")   # light green — GIVE
                fg_color = QColor("#1a5e35")

            running = round(running, 3)

            vals = [
                tx.get("date",""), tx.get("memo_no",""),
                tx_type, desc,
                f"{nwt:.3f}" if nwt else "—",
                touch,
                f"{fg:.3f}",
                cash_str,
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setBackground(bg)
                cell.setForeground(fg_color)
                cell.setTextAlignment(
                    Qt.AlignLeft | Qt.AlignVCenter if c == 3
                    else Qt.AlignCenter
                )
                self.tbl_tx.setItem(r, c, cell)

        dues = round(t_take_fg - t_give_fg, 3)
        self.lbl_r_txcount.setText(f"Txns: {len(txs_sorted)}")
        self.lbl_r_take_fg.setText(f"Fine Taken: {t_take_fg:.3f} g")
        self.lbl_r_give_fg.setText(f"Fine Given: {t_give_fg:.3f} g")
        self.lbl_r_dues.setText(f"Dues: {dues:.3f} g")
        color = "#c0392b" if dues > 0 else "#27ae60"
        self.lbl_r_dues.setStyleSheet(f"background:transparent;color:{color};font-weight:bold;")

        self._update_summary_bar()

    # ── Public refresh ────────────────────────────────────
    def refresh(self):
        self._all_transactions = get_all_transactions()
        self._setup_karigar_completer()
        self.fld_memo.setText(get_next_memo_no())
        self._reload_right()
        self._update_summary_bar()


# ============================================================
#  Karigar Directory Page
# ============================================================
class KarigarDirectoryPage(QWidget):

    def __init__(self):
        super().__init__()
        self._all_transactions: list = []
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
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        title = QLabel("Vendor Directory")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        root.addWidget(title)

        # Search
        sr = QHBoxLayout(); sr.setSpacing(8)
        sr.addWidget(_lbl("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Name, mobile or email…")
        self.txt_search.setFixedHeight(32)
        self.txt_search.textChanged.connect(self._apply_karigar_filter)
        sr.addWidget(self.txt_search); sr.addStretch()
        root.addLayout(sr)

        # Karigar table
        klbl = QLabel("All Vendors  —  click a row to view their transactions")
        klbl.setStyleSheet("font-weight:bold;color:#555;font-size:11px;")
        root.addWidget(klbl)

        _KC = ["Name", "Mobile", "Transactions", "Fine Gold Taken (g)", "Fine Gold Given (g)", "Dues (g)"]
        self.tbl_karigars = QTableWidget(0, len(_KC))
        self.tbl_karigars.setHorizontalHeaderLabels(_KC)
        hdr = self.tbl_karigars.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setMinimumSectionSize(60)
        for c in range(1, len(_KC)):
            hdr.setSectionResizeMode(c, QHeaderView.Interactive)
        for c, cw in {1:110, 2:90, 3:130, 4:130, 5:100}.items():
            self.tbl_karigars.setColumnWidth(c, cw)
        self.tbl_karigars.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_karigars.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_karigars.setAlternatingRowColors(True)
        self.tbl_karigars.verticalHeader().setVisible(False)
        self.tbl_karigars.verticalHeader().setDefaultSectionSize(34)
        self.tbl_karigars.setMinimumHeight(120)
        self.tbl_karigars.selectionModel().selectionChanged.connect(self._on_karigar_selected)
        root.addWidget(self.tbl_karigars)

        # History
        self.hist_lbl = QLabel("Transaction History  —  select a vendor above")
        self.hist_lbl.setStyleSheet("font-weight:bold;color:#555;font-size:11px;")
        root.addWidget(self.hist_lbl)

        # Filters
        flt = QHBoxLayout(); flt.setSpacing(8)
        flt.addWidget(_lbl("From:"))
        self.dt_from = _ClickDateEdit(QDate.currentDate().addMonths(-12))
        self.dt_from.setCalendarPopup(True); self.dt_from.setDisplayFormat("dd-MM-yyyy")
        self.dt_from.setFixedHeight(30); self.dt_from.setStyleSheet(_DTE)
        self.dt_from.dateChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.dt_from)

        flt.addWidget(_lbl("To:"))
        self.dt_to = _ClickDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True); self.dt_to.setDisplayFormat("dd-MM-yyyy")
        self.dt_to.setFixedHeight(30); self.dt_to.setStyleSheet(_DTE)
        self.dt_to.dateChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.dt_to)

        flt.addWidget(_lbl("Type:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["All", "TAKE", "GIVE"])
        self.cmb_type.setFixedHeight(30); self.cmb_type.setStyleSheet(_CMB)
        self.cmb_type.currentIndexChanged.connect(self._apply_tx_filter)
        flt.addWidget(self.cmb_type)

        btn_reset = _btn("Reset", "#7f8c8d", 30)
        btn_reset.clicked.connect(self._reset_filters)
        flt.addWidget(btn_reset); flt.addStretch()
        root.addLayout(flt)

        # Transaction table
        _TC = ["Date", "Memo", "Type", "Description", "Net Wt (g)", "Tounch", "Fine Gold (g)", "Cash (₹)", "Dues After (g)"]
        self.tbl_tx = QTableWidget(0, len(_TC))
        self.tbl_tx.setHorizontalHeaderLabels(_TC)
        hdr2 = self.tbl_tx.horizontalHeader()
        hdr2.setSectionResizeMode(3, QHeaderView.Stretch)
        hdr2.setMinimumSectionSize(52)
        for c in range(len(_TC)):
            if c != 3:
                hdr2.setSectionResizeMode(c, QHeaderView.Interactive)
        for c, cw in {0:86, 1:72, 2:52, 4:76, 5:62, 6:88, 7:80, 8:100}.items():
            self.tbl_tx.setColumnWidth(c, cw)
        self.tbl_tx.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_tx.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_tx.setAlternatingRowColors(True)
        self.tbl_tx.verticalHeader().setVisible(False)
        self.tbl_tx.verticalHeader().setDefaultSectionSize(30)
        self.tbl_tx.setMinimumHeight(240)
        root.addWidget(self.tbl_tx)

        # Footer
        sf = QFrame()
        sf.setStyleSheet("QFrame{background:white;border:1px solid #dde6ed;border-radius:5px;}")
        sl = QHBoxLayout(sf); sl.setContentsMargins(14,8,14,8); sl.setSpacing(20)
        self.lbl_count   = QLabel("Txns: 0")
        self.lbl_take_fg = QLabel("Fine Taken: 0.000 g")
        self.lbl_give_fg = QLabel("Fine Given: 0.000 g")
        self.lbl_dues    = QLabel("Dues: 0.000 g")
        for lbl in (self.lbl_count, self.lbl_take_fg, self.lbl_give_fg, self.lbl_dues):
            lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            lbl.setStyleSheet("background:transparent;color:#2c3e50;")
            sl.addWidget(lbl)
        sl.addStretch()
        root.addWidget(sf)

        self._selected_name = ""
        self._karigar_data: list = []

    def refresh(self):
        self._all_transactions = get_all_transactions()
        self._karigar_data = get_all_karigar_summaries()
        self._apply_karigar_filter()

    def _apply_karigar_filter(self):
        q = self.txt_search.text().strip().lower()
        data = [k for k in self._karigar_data
                if not q or q in k["name"].lower() or q in k.get("mobile","").lower()]
        self.tbl_karigars.setRowCount(0)
        for k in data:
            r = self.tbl_karigars.rowCount(); self.tbl_karigars.insertRow(r)
            dues = k["dues_fg"]
            vals = [k["name"], k.get("mobile",""), str(k["count"]),
                    f"{k['take_fg']:.3f}", f"{k['give_fg']:.3f}", f"{dues:.3f}"]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter if c == 0 else Qt.AlignCenter)
                if c == 5:
                    if dues > 0:
                        cell.setForeground(QColor("#27ae60"))
                        f_font = cell.font(); f_font.setBold(True); cell.setFont(f_font)
                    elif dues < 0:
                        cell.setForeground(QColor("#c0392b"))
                        f_font = cell.font(); f_font.setBold(True); cell.setFont(f_font)
                self.tbl_karigars.setItem(r, c, cell)

    def _on_karigar_selected(self):
        row = self.tbl_karigars.currentRow()
        if row < 0: return
        self._selected_name = self.tbl_karigars.item(row, 0).text()
        self.hist_lbl.setText(f"Transaction History  —  {self._selected_name}")
        self._apply_tx_filter()

    def _apply_tx_filter(self):
        if not self._selected_name: return
        d_from = self.dt_from.date().toString("yyyy-MM-dd")
        d_to   = self.dt_to.date().toString("yyyy-MM-dd")
        tf     = self.cmb_type.currentText()

        txs = [t for t in self._all_transactions
               if t.get("karigar_name","") == self._selected_name
               and d_from <= t.get("date","") <= d_to
               and (tf == "All" or t.get("tx_type","TAKE") == tf)]
        # Sort ascending to compute running dues correctly, then display newest-first
        txs_sorted = sorted(txs, key=lambda x: x.get("date",""))

        running = t_take = t_give = 0.0
        rows = []   # (vals, bg, row_fg)
        for tx in txs_sorted:
            tx_type = tx.get("tx_type","TAKE")
            fg = float(tx.get("total_fine_gold",0) or 0)
            cash = float(tx.get("total_payment", tx.get("give_cash",0)) or 0)

            if tx_type == "TAKE":
                running += fg; t_take += fg
                desc = "; ".join(f"{it.get('description','?')} x{it.get('pc',1)}" for it in tx.get("items",[]))
                nwt  = sum(float(it.get("net_wt",0)) for it in tx.get("items",[]))
                tounch_s = ", ".join(f"{it.get('tounch',0):.1f}%" for it in tx.get("items",[]))
                cash_str = "—"
                bg = QColor("#fde8e8")   # light red — TAKE
                row_fg = QColor("#7b1a1a")
            else:
                running -= fg; t_give += fg
                parts = []
                if tx.get("give_gold_net_wt",0): parts.append("Gold")
                if tx.get("give_cash",0):         parts.append("Cash")
                desc = " + ".join(parts) + " given" if parts else "Given"
                nwt = float(tx.get("give_gold_net_wt",0) or 0)
                tounch_s = f"{tx.get('give_gold_tounch',0):.1f}%" if tx.get("give_gold_net_wt") else "—"
                cash_str = f"{cash:,.2f}"
                bg = QColor("#e8f8ee")   # light green — GIVE
                row_fg = QColor("#1a5e35")

            running = round(running, 3)
            vals = [tx.get("date",""), tx.get("memo_no",""), tx_type, desc,
                    f"{nwt:.3f}" if nwt else "—", tounch_s, f"{fg:.3f}", cash_str, f"{running:.3f}"]
            rows.append((vals, bg, row_fg))

        self.tbl_tx.setRowCount(0)
        for vals, bg, row_fg in reversed(rows):
            r = self.tbl_tx.rowCount(); self.tbl_tx.insertRow(r)
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setBackground(bg)
                cell.setForeground(row_fg)
                cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter if c == 3 else Qt.AlignCenter)
                if c == 8:
                    fnt = cell.font(); fnt.setBold(True); cell.setFont(fnt)
                self.tbl_tx.setItem(r, c, cell)

        dues = round(t_take - t_give, 3)
        self.lbl_count.setText(f"Txns: {len(txs_sorted)}")
        self.lbl_take_fg.setText(f"Fine Taken: {t_take:.3f} g")
        self.lbl_give_fg.setText(f"Fine Given: {t_give:.3f} g")
        self.lbl_dues.setText(f"Dues: {dues:.3f} g")
        color = "#c0392b" if dues < 0 else ("#27ae60" if dues > 0 else "#2c3e50")
        self.lbl_dues.setStyleSheet(f"background:transparent;color:{color};font-weight:bold;")

    def _reset_filters(self):
        self.dt_from.setDate(QDate.currentDate().addMonths(-12))
        self.dt_to.setDate(QDate.currentDate())
        self.cmb_type.setCurrentIndex(0)
        self._apply_tx_filter()
