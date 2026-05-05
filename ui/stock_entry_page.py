# ============================================================
# ui/stock_entry_page.py — Stock Ledger (single unified form)
# ============================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QDoubleSpinBox, QSpinBox, QComboBox,
    QHeaderView, QAbstractItemView, QCompleter,
    QAbstractSpinBox, QDateEdit, QGridLayout, QFrame,
)
from PyQt5.QtCore import Qt, QDate, QEvent, QTimer
from PyQt5.QtGui import QFont, QColor

from services.stock_entry_service import (
    get_all_entries, add_entry, get_next_voucher_no,
)
from services.metal_service import get_metals
from services.item_catalog_service import get_item_by_name, get_item_by_code, get_names as get_catalog_names

PURITY_OPTIONS   = ["22Kt", "18Kt", "14Kt", "92.5", "99.9", "60-70", "Other"]
LOCATION_OPTIONS = ["SHOWROOM", "TRANSACTION"]
_FLD_H = 30

# ── Styles ───────────────────────────────────────────────────
_GRP = (
    "QGroupBox{font-size:12px;font-weight:bold;color:#2c3e50;"
    "border:1px solid #dde6ed;border-radius:8px;margin-top:10px;padding-top:6px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;background:white;}"
)
_SEC_LBL_IN  = "color:#155724;font-size:11px;font-weight:700;"
_SEC_LBL_OUT = "color:#7b1f1f;font-size:11px;font-weight:700;"
_FILTER_GRP = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#555;"
    "border:1px solid #dfe6e9;border-radius:6px;margin-top:8px;padding-top:4px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}"
)


# ── Widget factories ─────────────────────────────────────────
def _lbl(text: str, style: str = "color:#444;font-size:11px;font-weight:600;") -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(style)
    return l


def _line(ph: str = "") -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(ph)
    e.setFixedHeight(_FLD_H)
    e.setStyleSheet(
        "QLineEdit{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
        "font-size:12px;background:white;}"
        "QLineEdit:focus{border:2px solid #3498db;background:#eaf6fd;}"
    )
    return e


def _dspn(dec: int = 3, max_v: float = 9_999_999, readonly: bool = False) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(0, max_v)
    s.setDecimals(dec)
    s.setFixedHeight(_FLD_H)
    s.setButtonSymbols(QAbstractSpinBox.NoButtons)
    s.setReadOnly(readonly)
    s.setStyleSheet(
        "QDoubleSpinBox{border:1px solid #27ae60;border-radius:4px;padding:0 7px;"
        "font-size:12px;font-weight:bold;background:#eafaf1;color:#1e8449;}"
        if readonly else
        "QDoubleSpinBox{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
        "font-size:12px;background:white;}"
        "QDoubleSpinBox:focus{border:2px solid #3498db;background:#eaf6fd;}"
    )
    return s


def _ispn(val: int = 0) -> QSpinBox:
    s = QSpinBox()
    s.setRange(0, 99_999)
    s.setValue(val)
    s.setFixedHeight(_FLD_H)
    s.setButtonSymbols(QAbstractSpinBox.NoButtons)
    s.setStyleSheet(
        "QSpinBox{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
        "font-size:12px;background:white;}"
        "QSpinBox:focus{border:2px solid #3498db;background:#eaf6fd;}"
    )
    return s


def _cmb(items=(), editable: bool = False) -> QComboBox:
    c = QComboBox()
    c.addItems(items)
    c.setFixedHeight(_FLD_H)
    c.setEditable(editable)
    c.setStyleSheet(
        "QComboBox{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
        "font-size:12px;background:white;}"
        "QComboBox:focus{border:2px solid #3498db;}"
        "QComboBox::drop-down{border:none;width:18px;}"
    )
    return c


def _date_edit() -> QDateEdit:
    d = QDateEdit(QDate.currentDate())
    d.setCalendarPopup(True)
    d.setFixedHeight(_FLD_H)
    d.setDisplayFormat("dd-MM-yyyy")
    d.setStyleSheet(
        "QDateEdit{border:1px solid #ced4da;border-radius:4px;padding:0 7px;"
        "font-size:12px;background:white;}"
        "QDateEdit::drop-down{border:none;}"
    )
    return d


def _sep_label(text: str, style: str) -> QWidget:
    """Horizontal rule with a centred label — used as section divider."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 4, 0, 2)
    h.setSpacing(6)
    line1 = QFrame(); line1.setFrameShape(QFrame.HLine)
    line1.setStyleSheet("QFrame{color:#d5dbdb;}")
    lbl = QLabel(text)
    lbl.setStyleSheet(style + "padding:0 4px;")
    line2 = QFrame(); line2.setFrameShape(QFrame.HLine)
    line2.setStyleSheet("QFrame{color:#d5dbdb;}")
    h.addWidget(line1, 1)
    h.addWidget(lbl)
    h.addWidget(line2, 1)
    return w


# ═══════════════════════════════════════════════════════════
class StockEntryPage(QWidget):

    def __init__(self):
        super().__init__()
        self._entries: list[dict] = []
        self._filtered: list[dict] = []
        self._metals: list[dict] = []
        self._sort_col: int = -1
        self._sort_asc: bool = True
        self._build_ui()

    # ──────────────────────────────────────────────────────
    #  Master layout
    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(8)

        # Title bar — no clear button
        tr = QHBoxLayout()
        t = QLabel("📦  Stock Entry")
        t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        tr.addWidget(t)
        tr.addStretch()
        root.addLayout(tr)

        # Form + table split
        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self._build_form(), 38)
        body.addWidget(self._build_right(), 62)
        root.addLayout(body, 1)

    # ──────────────────────────────────────────────────────
    #  Left — unified entry form
    # ──────────────────────────────────────────────────────
    def _build_form(self) -> QGroupBox:
        grp = QGroupBox("Entry Details")
        grp.setStyleSheet(_GRP)
        g = QGridLayout(grp)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(5)
        g.setContentsMargins(12, 14, 12, 12)

        def row(r: int, l0: str, w0, l1: str = "", w1=None,
                s0: str = "", s1: str = ""):
            lbl0 = _lbl(l0, s0 or "color:#444;font-size:11px;font-weight:600;")
            lbl0.setMaximumWidth(82)
            g.addWidget(lbl0, r, 0)
            g.addWidget(w0, r, 1)
            if l1:
                lbl1 = _lbl(l1, s1 or "color:#444;font-size:11px;font-weight:600;")
                lbl1.setMaximumWidth(82)
                g.addWidget(lbl1, r, 2)
                g.addWidget(w1, r, 3)

        # ── Common fields ──────────────────────────────────
        self.voucher_no   = _line("VCH-0001")
        self.voucher_date = _date_edit()
        row(0, "Voucher No *", self.voucher_no, "Date *", self.voucher_date)

        self.metal = _cmb()
        self.item  = _line("Search item name…")
        row(1, "Metal", self.metal, "Item Name *", self.item)

        self.subname = _line("Supplier name")
        self.purity  = _cmb(PURITY_OPTIONS, editable=True)
        row(2, "Supplier Name", self.subname, "Purity", self.purity)

        # ── IN section ────────────────────────────────────
        g.addWidget(_sep_label("─  Stock IN Details  ─", _SEC_LBL_IN), 3, 0, 1, 4)

        self.in_dabba_name = _line("Box / dabba label")
        self.in_dabba_wt   = _dspn(3)
        row(4, "Dabba Name", self.in_dabba_name, "Dabba Wt (g)", self.in_dabba_wt,
            _SEC_LBL_IN, _SEC_LBL_IN)

        self.in_gross_wt   = _dspn(3)
        self.in_plastic_wt = _dspn(3)
        self.in_gross_wt.valueChanged.connect(self._sync_net_wt)
        self.in_plastic_wt.valueChanged.connect(self._sync_net_wt)
        row(5, "Gross Wt (g)", self.in_gross_wt, "Plastic Wt (g)", self.in_plastic_wt,
            _SEC_LBL_IN, _SEC_LBL_IN)

        self.in_qty     = _ispn(0)
        self.in_less_wt = _dspn(3)
        self.in_less_wt.valueChanged.connect(self._sync_net_wt)
        row(6, "Qtrn In", self.in_qty, "Less Wt (g)", self.in_less_wt,
            _SEC_LBL_IN, _SEC_LBL_IN)

        self.in_dia_wt = _dspn(3)
        self.in_net_wt = _dspn(3, readonly=True)
        self.in_dia_wt.valueChanged.connect(self._sync_net_wt)
        row(7, "Dia Wt (g)", self.in_dia_wt, "Net Wt (g)", self.in_net_wt,
            _SEC_LBL_IN, _SEC_LBL_IN)

        self.in_location = _cmb(LOCATION_OPTIONS, editable=True)
        row(8, "Location", self.in_location, s0=_SEC_LBL_IN)

        # ── OUT section ───────────────────────────────────
        g.addWidget(_sep_label("─  Stock OUT Details  ─", _SEC_LBL_OUT), 9, 0, 1, 4)

        self.out_gross_wt = _dspn(3)
        self.out_net_wt   = _dspn(3)
        row(10, "Gross Wt (g)", self.out_gross_wt, "Net Wt (g)", self.out_net_wt,
            _SEC_LBL_OUT, _SEC_LBL_OUT)

        self.out_qty = _ispn(0)
        row(11, "Qty Out", self.out_qty, s0=_SEC_LBL_OUT)

        # ── Footer ────────────────────────────────────────
        g.addWidget(_sep_label("", ""), 12, 0, 1, 4)

        self.remarks = _line("Remarks (optional)")
        row(13, "Remarks", self.remarks)
        g.addWidget(self.remarks, 13, 1, 1, 3)

        btn_save = QPushButton("💾  Save Entry")
        btn_save.setFixedHeight(38)
        btn_save.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:6px;"
            "font-size:13px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        btn_save.clicked.connect(self._save_entry)
        g.addWidget(btn_save, 14, 0, 1, 4)

        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)

        self._setup_enter_nav()
        return grp

    # ──────────────────────────────────────────────────────
    #  Enter-key navigation
    # ──────────────────────────────────────────────────────
    def _setup_enter_nav(self):
        self._nav_chain = [
            self.voucher_no,
            self.voucher_date,
            self.metal,
            self.item,
            self.subname,
            self.purity,
            self.in_dabba_name,
            self.in_dabba_wt,
            self.in_gross_wt,
            self.in_plastic_wt,
            self.in_qty,
            self.in_less_wt,
            self.in_dia_wt,
            self.in_location,
            self.out_gross_wt,
            self.out_net_wt,
            self.out_qty,
            self.remarks,
        ]
        for i, w in enumerate(self._nav_chain):
            w._nav_idx = i
            if isinstance(w, QLineEdit):
                w.returnPressed.connect(lambda idx=i: self._focus_next(idx))
            else:
                w.installEventFilter(self)

    def _focus_next(self, current_idx: int):
        nxt = current_idx + 1
        if nxt < len(self._nav_chain):
            w = self._nav_chain[nxt]
            QTimer.singleShot(0, lambda: (w.setFocus(),
                                          w.selectAll() if hasattr(w, "selectAll") else None))

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.KeyPress
                and event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and hasattr(obj, "_nav_idx")):
            QTimer.singleShot(0, lambda: self._focus_next(obj._nav_idx))
            return False
        return super().eventFilter(obj, event)

    # ──────────────────────────────────────────────────────
    #  Right panel — filter bar + table
    # ──────────────────────────────────────────────────────
    def _build_right(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        v.addWidget(self._build_filter_bar())
        self._build_table()
        v.addWidget(self.tbl, 1)
        return w

    # ──────────────────────────────────────────────────────
    #  Filter bar — two rows to prevent overflow
    # ──────────────────────────────────────────────────────
    def _build_filter_bar(self) -> QGroupBox:
        grp = QGroupBox("Filters")
        grp.setStyleSheet(_FILTER_GRP)
        vl = QVBoxLayout(grp)
        vl.setSpacing(5)
        vl.setContentsMargins(10, 6, 10, 8)

        row1 = QHBoxLayout(); row1.setSpacing(8)
        row2 = QHBoxLayout(); row2.setSpacing(8)

        def _f(hl, label, widget):
            hl.addWidget(_lbl(label))
            hl.addWidget(widget)

        # Row 1: Type, Metal, Purity, Sub Name, Item
        self.f_type = _cmb(["All", "IN", "OUT"])
        self.f_type.setFixedWidth(72)
        self.f_type.currentIndexChanged.connect(self._do_filter)
        _f(row1, "Type:", self.f_type)

        self.f_metal = _cmb(["All"])
        self.f_metal.setFixedWidth(110)
        self.f_metal.currentIndexChanged.connect(self._do_filter)
        _f(row1, "Metal:", self.f_metal)

        self.f_purity = _cmb(["All"])
        self.f_purity.setFixedWidth(86)
        self.f_purity.currentIndexChanged.connect(self._do_filter)
        _f(row1, "Purity:", self.f_purity)

        self.f_subname = _line("supplier name…")
        self.f_subname.setFixedWidth(110)
        self.f_subname.textChanged.connect(self._on_filter_text)
        _f(row1, "Supplier Name:", self.f_subname)

        self.f_item = _line("item name…")
        self.f_item.setFixedWidth(120)
        self.f_item.textChanged.connect(self._on_filter_text)
        _f(row1, "Item:", self.f_item)

        row1.addStretch()

        # Row 2: Net Wt range, Location, Reset
        self.f_wt_min = _dspn(3)
        self.f_wt_min.setFixedWidth(82)
        self.f_wt_min.valueChanged.connect(self._do_filter)
        _f(row2, "Net Wt ≥:", self.f_wt_min)

        self.f_wt_max = _dspn(3)
        self.f_wt_max.setFixedWidth(82)
        self.f_wt_max.setValue(9_999.999)
        self.f_wt_max.valueChanged.connect(self._do_filter)
        _f(row2, "≤:", self.f_wt_max)

        self.f_location = _cmb(["All"] + LOCATION_OPTIONS)
        self.f_location.setFixedWidth(130)
        self.f_location.currentIndexChanged.connect(self._do_filter)
        _f(row2, "Location:", self.f_location)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedHeight(28)
        btn_reset.setStyleSheet(
            "QPushButton{background:#7f8c8d;color:white;border-radius:4px;"
            "padding:2px 12px;font-size:11px;border:none;}"
            "QPushButton:hover{background:#626567;}"
        )
        btn_reset.clicked.connect(self._reset_filters)
        row2.addWidget(btn_reset)
        row2.addStretch()

        vl.addLayout(row1)
        vl.addLayout(row2)
        return grp

    # ──────────────────────────────────────────────────────
    #  Table (12 columns, no delete button)
    # ──────────────────────────────────────────────────────
    def _build_table(self):
        self.tbl = QTableWidget()
        _H = ["Group", "Product", "Supplier Name",
              "Wt In (g)", "Wt Out (g)", "Qty In", "Qty Out",
              "Date", "Dabba", "Bill / Voucher", "Remarks", "Type"]
        self.tbl.setColumnCount(len(_H))
        self.tbl.setHorizontalHeaderLabels(_H)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(1,  QHeaderView.Stretch)
        hdr.setSectionResizeMode(9,  QHeaderView.Stretch)
        _fixed = {0:80, 2:88, 3:80, 4:80, 5:65, 6:65,
                  7:90, 8:88, 10:100, 11:110}
        for c, w in _fixed.items():
            self.tbl.setColumnWidth(c, w)
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.verticalHeader().setDefaultSectionSize(30)
        self.tbl.setMinimumHeight(180)
        hdr.sectionClicked.connect(self._on_header_click)
        hdr.setCursor(Qt.PointingHandCursor)

    # ──────────────────────────────────────────────────────
    #  Net Wt auto-calc: gross - plastic - less_wt - dia_wt
    # ──────────────────────────────────────────────────────
    def _sync_net_wt(self):
        net = max(0.0, round(
            self.in_gross_wt.value()
            - self.in_plastic_wt.value()
            - self.in_less_wt.value()
            - self.in_dia_wt.value(), 3
        ))
        self.in_net_wt.blockSignals(True)
        self.in_net_wt.setValue(net)
        self.in_net_wt.blockSignals(False)

    # ──────────────────────────────────────────────────────
    #  Save — auto-detect IN vs OUT from filled fields
    # ──────────────────────────────────────────────────────
    def _save_entry(self):
        v_no = self.voucher_no.text().strip()
        item = self.item.text().strip()

        if not v_no:
            QMessageBox.warning(self, "Validation", "Voucher No is required.")
            self.voucher_no.setFocus(); return
        if not item:
            QMessageBox.warning(self, "Validation", "Item Name is required.")
            self.item.setFocus(); return

        has_in  = self.in_gross_wt.value() > 0 or self.in_qty.value() > 0
        has_out = (self.out_gross_wt.value() > 0
                   or self.out_net_wt.value() > 0
                   or self.out_qty.value() > 0)

        if has_in and has_out:
            QMessageBox.warning(
                self, "Validation",
                "Both IN and OUT fields are filled.\n"
                "Please fill only IN details or only OUT details for one entry."
            )
            return

        if not has_in and not has_out:
            QMessageBox.warning(
                self, "Validation",
                "No details filled.\n"
                "Fill IN fields (Gross Wt / Qtrn In) or OUT fields (Out Gross Wt / Qty Out)."
            )
            return

        entry_type = "IN" if has_in else "OUT"

        entry = {
            "entry_type":   entry_type,
            "voucher_no":   v_no,
            "voucher_date": self.voucher_date.date().toString("yyyy-MM-dd"),
            "metal_type":   self.metal.currentText(),
            "item_name":    item,
            "sub_name":     self.subname.text().strip(),
            "purity":       self.purity.currentText(),
            # IN fields
            "dabba_name":   self.in_dabba_name.text().strip(),
            "dabba_wt":     self.in_dabba_wt.value(),
            "gross_wt":     self.in_gross_wt.value(),
            "plastic_wt":   self.in_plastic_wt.value(),
            "qty_in":       self.in_qty.value(),
            "less_wt":      self.in_less_wt.value(),
            "dia_wt":       self.in_dia_wt.value(),
            "net_wt":       self.in_net_wt.value(),
            "location":     self.in_location.currentText() if entry_type == "IN" else "OUT",
            # OUT fields
            "out_gross_wt": self.out_gross_wt.value(),
            "out_net_wt":   self.out_net_wt.value(),
            "qty_out":      self.out_qty.value(),
            "remarks":      self.remarks.text().strip(),
        }

        if add_entry(entry):
            QMessageBox.information(
                self, "Saved",
                f"Stock {entry_type} entry saved — '{item}'."
            )
            self._clear_form()
            self.voucher_no.setText(get_next_voucher_no())
            self.refresh()
        else:
            QMessageBox.critical(self, "Error", "Could not save entry.")

    # ──────────────────────────────────────────────────────
    #  Filter logic
    # ──────────────────────────────────────────────────────
    def _on_filter_text(self, text: str):
        if len(text.strip()) >= 2 or text.strip() == "":
            self._do_filter()

    def _do_filter(self):
        tf  = self.f_type.currentText()
        mf  = self.f_metal.currentText()
        pf  = self.f_purity.currentText()
        snf = self.f_subname.text().strip().lower()
        itf = self.f_item.text().strip().lower()
        wlo = self.f_wt_min.value()
        whi = self.f_wt_max.value()
        lf  = self.f_location.currentText()

        out = []
        for e in self._entries:
            et = e.get("entry_type", "IN")
            if tf != "All" and et != tf:                               continue
            if mf != "All" and e.get("metal_type", "") != mf:         continue
            if pf != "All" and e.get("purity", "") != pf:             continue
            if snf and snf not in e.get("sub_name", "").lower():      continue
            if itf and itf not in e.get("item_name", "").lower():     continue
            net = e.get("net_wt", 0.0) if et == "IN" else e.get("out_net_wt", 0.0)
            if net < wlo or net > whi:                                 continue
            if lf != "All":
                loc = e.get("location", "") if et == "IN" else "OUT"
                if loc != lf:                                          continue
            out.append(e)

        self._filtered = out
        self._populate_table()

    # ──────────────────────────────────────────────────────
    #  Populate table
    # ──────────────────────────────────────────────────────
    def _populate_table(self):
        self.tbl.setRowCount(0)
        ti = to = qi = qo = 0.0

        for e in self._filtered:
            r     = self.tbl.rowCount()
            is_in = e.get("entry_type") == "IN"
            self.tbl.insertRow(r)

            loc    = e.get("location", "") if is_in else "OUT"
            wt_in  = f"{e.get('net_wt', 0.0):.3f}" if is_in else ""
            wt_out = "" if is_in else f"{e.get('out_net_wt', 0.0):.3f}"
            qi_s   = str(e.get("qty_in",  0)) if is_in else ""
            qo_s   = "" if is_in else str(e.get("qty_out", 0))

            vals = [
                e.get("metal_type",   ""),
                e.get("item_name",    ""),
                e.get("sub_name",     ""),
                wt_in, wt_out, qi_s, qo_s,
                e.get("voucher_date", ""),
                e.get("dabba_name",   ""),
                e.get("voucher_no",   ""),
                e.get("remarks",      ""),
                loc,
            ]
            _right = {3, 4, 5, 6}
            bg = QColor("#f0fdf4") if is_in else QColor("#fff5f5")
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(
                    Qt.AlignRight | Qt.AlignVCenter if c in _right else Qt.AlignCenter
                )
                cell.setBackground(bg)
                self.tbl.setItem(r, c, cell)

            tc = self.tbl.item(r, 11)
            if tc:
                tc.setForeground(QColor("#1e8449" if is_in else "#c0392b"))
                f = tc.font(); f.setBold(True); tc.setFont(f)

            if is_in:
                ti += e.get("net_wt",     0.0); qi += e.get("qty_in",  0)
            else:
                to += e.get("out_net_wt", 0.0); qo += e.get("qty_out", 0)

        # Footer totals row
        if self._filtered:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            fb = QColor("#eaf2ff")
            for c in range(12):
                v = {0: "TOTAL", 3: f"{ti:.3f}", 4: f"{to:.3f}",
                     5: str(int(qi)), 6: str(int(qo))}.get(c, "")
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setBackground(fb)
                f = cell.font(); f.setBold(True); cell.setFont(f)
                self.tbl.setItem(r, c, cell)

    # ──────────────────────────────────────────────────────
    #  Sort
    # ──────────────────────────────────────────────────────
    _SK = {0: "metal_type", 1: "item_name", 2: "sub_name",
           3: "net_wt", 4: "out_net_wt", 5: "qty_in", 6: "qty_out",
           7: "voucher_date", 8: "dabba_name", 9: "voucher_no",
           10: "remarks", 11: "location"}

    def _on_header_click(self, col: int):
        if self._sort_col == col:
            if self._sort_asc:
                self._sort_col = -1; self._do_filter(); return
            self._sort_asc = True
        else:
            self._sort_col = col; self._sort_asc = False
        key = self._SK.get(col)
        if key:
            def _k(e):
                v = e.get(key, "")
                try:    return (0, float(v))
                except: return (1, str(v).lower())
            self._filtered = sorted(self._filtered, key=_k, reverse=not self._sort_asc)
        self._populate_table()

    # ──────────────────────────────────────────────────────
    #  Reload helpers
    # ──────────────────────────────────────────────────────
    def _reload_metals(self):
        self._metals = get_metals()
        names = [""] + [m.get("name", "") for m in self._metals]
        curr = self.metal.currentText()
        self.metal.blockSignals(True)
        self.metal.clear(); self.metal.addItems(names)
        self.metal.setCurrentIndex(max(0, self.metal.findText(curr)))
        self.metal.blockSignals(False)

        fc = self.f_metal.currentText()
        self.f_metal.blockSignals(True)
        self.f_metal.clear(); self.f_metal.addItem("All")
        for m in self._metals: self.f_metal.addItem(m.get("name", ""))
        self.f_metal.setCurrentIndex(max(0, self.f_metal.findText(fc)))
        self.f_metal.blockSignals(False)

    def _reload_purity_filter(self):
        purities = sorted({e.get("purity", "") for e in self._entries if e.get("purity")})
        curr = self.f_purity.currentText()
        self.f_purity.blockSignals(True)
        self.f_purity.clear(); self.f_purity.addItem("All")
        for p in purities: self.f_purity.addItem(p)
        self.f_purity.setCurrentIndex(max(0, self.f_purity.findText(curr)))
        self.f_purity.blockSignals(False)

    def _reload_location_dropdown(self):
        """Populate the form Location combo with defaults + any custom locations from saved entries."""
        used = {e.get("location", "") for e in self._entries
                if e.get("entry_type") == "IN" and e.get("location")}
        options = list(LOCATION_OPTIONS)
        for loc in sorted(used):
            if loc not in options:
                options.append(loc)
        curr = self.in_location.currentText()
        self.in_location.blockSignals(True)
        self.in_location.clear()
        self.in_location.addItems(options)
        idx = self.in_location.findText(curr)
        if idx >= 0:
            self.in_location.setCurrentIndex(idx)
        elif curr:
            self.in_location.setCurrentText(curr)
        self.in_location.blockSignals(False)

    def _reload_location_filter(self):
        """Sync the filter Location combo with all known locations."""
        used = {e.get("location", "") for e in self._entries
                if e.get("entry_type") == "IN" and e.get("location")}
        options = list(LOCATION_OPTIONS)
        for loc in sorted(used):
            if loc not in options:
                options.append(loc)
        curr = self.f_location.currentText()
        self.f_location.blockSignals(True)
        self.f_location.clear()
        self.f_location.addItem("All")
        self.f_location.addItems(options)
        self.f_location.setCurrentIndex(max(0, self.f_location.findText(curr)))
        self.f_location.blockSignals(False)

    def _reload_item_completer(self):
        names = get_catalog_names()
        c = QCompleter(names, self.item)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setFilterMode(Qt.MatchContains)
        self.item.setCompleter(c)
        try:   c.activated.disconnect()
        except Exception: pass
        c.activated.connect(self._autofill_item)
        # Guard: connect returnPressed only once across multiple refresh() calls
        if not getattr(self, '_item_autofill_connected', False):
            self.item.returnPressed.connect(lambda: self._autofill_item(self.item.text().strip()))
            self._item_autofill_connected = True

    def _autofill_item(self, name: str):
        if not name: return
        cat = get_item_by_name(name)
        if not cat:
            # Try shortcut code lookup and fill the full name into the field
            cat = get_item_by_code(name)
            if cat:
                self.item.blockSignals(True)
                self.item.setText(cat["name"])
                self.item.blockSignals(False)
        if not cat: return
        purity = cat.get("purity", "")
        if purity:
            idx = self.purity.findText(purity)
            self.purity.setCurrentIndex(idx) if idx >= 0 else self.purity.setCurrentText(purity)
        mid = cat.get("metal_id", "")
        if mid:
            for m in self._metals:
                if m.get("id") == mid:
                    idx = self.metal.findText(m.get("name", ""))
                    if idx >= 0: self.metal.setCurrentIndex(idx)
                    break

    # ──────────────────────────────────────────────────────
    #  Clear / Reset
    # ──────────────────────────────────────────────────────
    def _clear_form(self):
        self.item.clear(); self.subname.clear(); self.remarks.clear()
        self.metal.setCurrentIndex(0)
        self.purity.setCurrentIndex(0)
        self.voucher_date.setDate(QDate.currentDate())
        self.in_dabba_name.clear()
        for spn in (self.in_dabba_wt, self.in_gross_wt, self.in_plastic_wt,
                    self.in_less_wt, self.in_dia_wt, self.in_net_wt):
            spn.blockSignals(True); spn.setValue(0.0); spn.blockSignals(False)
        self.in_qty.setValue(0)
        self.in_location.setCurrentIndex(0)
        self.out_gross_wt.setValue(0.0)
        self.out_net_wt.setValue(0.0)
        self.out_qty.setValue(0)

    def _reset_filters(self):
        for w in (self.f_type, self.f_metal, self.f_purity, self.f_location):
            w.blockSignals(True); w.setCurrentIndex(0); w.blockSignals(False)
        self.f_subname.clear(); self.f_item.clear()
        self.f_wt_min.setValue(0.0); self.f_wt_max.setValue(9_999.999)
        self._do_filter()

    # ──────────────────────────────────────────────────────
    #  Public refresh
    # ──────────────────────────────────────────────────────
    def refresh(self):
        self._entries = get_all_entries()
        self._reload_metals()
        self._reload_purity_filter()
        self._reload_item_completer()
        self._reload_location_dropdown()
        self._reload_location_filter()
        if not self.voucher_no.text().strip():
            self.voucher_no.setText(get_next_voucher_no())
        self._do_filter()
