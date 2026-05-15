# ============================================================
# ui/invoice_detail_dialog.py  –  Invoice Detail Viewer
# Shows full customer info + purchase history for a saved invoice.
# ============================================================

from collections import OrderedDict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame, QGroupBox,
    QScrollArea, QWidget, QHeaderView, QAbstractItemView,
    QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from app.utils import format_currency


def _build_metals_map() -> dict:
    """purity.upper() → metal name, e.g. '22KT' → 'Gold'"""
    try:
        from services.metal_service import get_metals
        return {m.get('purity', '').strip().upper(): m.get('name', '')
                for m in get_metals() if m.get('purity')}
    except Exception:
        return {}


def _metal_label(purity: str, metals_map: dict) -> str:
    metal = metals_map.get(purity.strip().upper(), '')
    return f"{metal} {purity}".strip() if metal else purity


def _card(title: str) -> tuple:
    """Return (QGroupBox, inner QVBoxLayout) styled as a card."""
    grp = QGroupBox(title)
    grp.setStyleSheet(
        "QGroupBox{background:white;border:1px solid #e0e0e0;border-radius:6px;"
        "margin-top:18px;padding-top:6px;font-weight:bold;font-size:12px;color:#2c3e50;}"
        "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}"
    )
    lay = QVBoxLayout(grp)
    lay.setContentsMargins(12, 8, 12, 10)
    lay.setSpacing(6)
    return grp, lay


def _kv_row(key: str, value: str, bold_val: bool = False) -> QHBoxLayout:
    """One key : value row."""
    row = QHBoxLayout()
    lbl_k = QLabel(key + ":")
    lbl_k.setStyleSheet("color:#7f8c8d; font-size:12px;")
    lbl_k.setFixedWidth(130)
    lbl_v = QLabel(value or "—")
    lbl_v.setStyleSheet(
        f"color:#2c3e50; font-size:12px;{'font-weight:bold;' if bold_val else ''}"
    )
    lbl_v.setWordWrap(True)
    row.addWidget(lbl_k)
    row.addWidget(lbl_v, 1)
    return row


class InvoiceDetailDialog(QDialog):
    def __init__(self, invoice: dict, parent=None,
                 on_edit=None, on_duplicate=None):
        super().__init__(parent)
        self._invoice     = invoice
        self._on_edit      = on_edit
        self._on_duplicate = on_duplicate
        inv_no = invoice.get("invoice_number", "")
        self.setWindowTitle(f"Invoice Details  —  {inv_no}")
        self.setMinimumWidth(780)
        self.setMinimumHeight(620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header bar ─────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet("background:#2c3e50;")
        hdr.setFixedHeight(54)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(18, 0, 18, 0)

        inv = self._invoice
        inv_no   = inv.get("invoice_number", "")
        inv_date = inv.get("date", "")
        inv_time = inv.get("time", "")

        lbl_title = QLabel(f"Invoice  {inv_no}")
        lbl_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_title.setStyleSheet("color:white;")

        lbl_dt = QLabel(f"{inv_date}  {inv_time}")
        lbl_dt.setStyleSheet("color:#bdc3c7; font-size:12px;")

        hl.addWidget(lbl_title)
        hl.addStretch()
        hl.addWidget(lbl_dt)
        outer.addWidget(hdr)

        # ── Scrollable body ────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#f5f6fa;")

        body = QWidget()
        body.setStyleSheet("background:#f5f6fa;")
        root = QVBoxLayout(body)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ── Customer Details ───────────────────────────────────
        cust_grp, cl = _card("Customer Details")
        cust_left  = QVBoxLayout()
        cust_right = QVBoxLayout()

        cust_left.addLayout(_kv_row("Name",    inv.get("customer_name",    ""), bold_val=True))
        cust_left.addLayout(_kv_row("Mobile",  inv.get("customer_mobile",  "")))
        cust_left.addLayout(_kv_row("Email",   inv.get("customer_email",   "")))
        cust_left.addLayout(_kv_row("Address", inv.get("customer_address", "")))

        cust_right.addLayout(_kv_row("GST No.",  inv.get("customer_gst",     "")))
        cust_right.addLayout(_kv_row("Aadhaar",  inv.get("customer_aadhaar", "")))
        cust_right.addLayout(_kv_row("PAN No.",  inv.get("customer_pan",     "")))

        cust_cols = QHBoxLayout()
        cust_cols.setSpacing(20)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#e0e0e0;")

        cust_cols.addLayout(cust_left, 3)
        cust_cols.addWidget(sep)
        cust_cols.addLayout(cust_right, 2)
        cl.addLayout(cust_cols)
        root.addWidget(cust_grp)

        # ── Items Purchased ────────────────────────────────────
        items_grp, il = _card("Items Purchased")
        tbl = QTableWidget()
        tbl.setColumnCount(11)
        tbl.setHorizontalHeaderLabels([
            "#", "Tag/RFID", "Item Name", "HUID/Remarks", "Purity", "Pcs",
            "Gross Wt (g)", "Nett Wt (g)", "Rate ₹/g",
            "Making ₹", "Total ₹"
        ])
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for col, w in {0: 28, 1: 90, 3: 110, 4: 72, 5: 40, 6: 86, 7: 86, 8: 76, 9: 86, 10: 100}.items():
            tbl.setColumnWidth(col, w)
            tbl.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            "QTableWidget{border:1px solid #e0e0e0;border-radius:4px;}"
            "QHeaderView::section{background:#34495e;color:white;font-weight:bold;"
            "font-size:11px;padding:5px;border:none;}"
        )

        items      = inv.get("items", [])
        metals_map = _build_metals_map()

        def _item_metal(purity: str) -> str:
            metal = metals_map.get(purity.strip().upper(), '')
            return metal if metal else purity

        # Group items by metal name (Gold, Silver, …)
        groups = OrderedDict()
        for it in items:
            p  = (it.get('purity') or 'Other').strip()
            mn = _item_metal(p)
            groups.setdefault((mn, p), []).append(it)

        SUBT_BG = QColor('#e4e4e4')
        SUBT_FG = QColor('#2c3e50')

        row_idx    = 0
        serial     = 0
        total_rows = len(items) + len(groups)   # always one total row per metal
        tbl.setRowCount(total_rows)

        for (metal_name, metal_purity), grp_items in groups.items():
            gw_grp = nw_grp = amt_grp = 0.0

            for it in grp_items:
                gw  = float(it.get("weight",        0))
                lw  = float(it.get("less_weight",   0))
                nw  = round(gw - lw, 3)
                mk  = float(it.get("making_charge", 0))
                amt = float(it.get("total",         0))
                gw_grp += gw; nw_grp += nw; amt_grp += amt
                serial += 1

                vals = [
                    str(serial),
                    it.get("tag",  ""),
                    it.get("name", ""),
                    it.get("huid", ""),
                    it.get("purity", ""),
                    str(it.get("quantity", 1)),
                    f"{gw:.3f}",
                    f"{nw:.3f}",
                    f"{float(it.get('rate', 0)):.2f}",
                    f"{mk:,.2f}",
                    f"{amt:,.2f}",
                ]
                for c, v in enumerate(vals):
                    cell = QTableWidgetItem(v)
                    cell.setTextAlignment(Qt.AlignCenter)
                    if c == 2:
                        cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    if c == 10:
                        cell.setForeground(QColor("#27ae60"))
                        cell.setFont(QFont("Segoe UI", 9, QFont.Bold))
                    tbl.setItem(row_idx, c, cell)
                row_idx += 1

            # Metal total row — always shown
            _grp_display = f"{metal_name} ({metal_purity})" if metal_purity and metal_purity != metal_name else metal_name
            lbl = f"{_grp_display} Total"
            sub_vals = [
                "", lbl, "", "", "", "",
                f"{gw_grp:.3f}",
                f"{nw_grp:.3f}",
                "", "",
                f"{amt_grp:,.2f}",
            ]
            for c, v in enumerate(sub_vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setBackground(SUBT_BG)
                cell.setForeground(SUBT_FG)
                cell.setFont(QFont("Segoe UI", 9, QFont.Bold))
                if c == 1:
                    cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if c == 10:
                    cell.setForeground(QColor("#27ae60"))
                tbl.setItem(row_idx, c, cell)
            tbl.setRowHeight(row_idx, 28)
            row_idx += 1

        tbl.setMinimumHeight(min(42 * max(total_rows, 1) + 40, 320))
        il.addWidget(tbl)
        root.addWidget(items_grp)

        # ── Payment & Totals (side-by-side) ────────────────────
        pt_row = QHBoxLayout(); pt_row.setSpacing(12)

        # Payment Details
        pay_grp, pl = _card("Payment Details")
        def _prow(label, val):
            if float(val or 0) == 0 and label not in ("Due Amount",):
                return
            pl.addLayout(_kv_row(label, f"₹ {float(val or 0):,.2f}"))

        _prow("Cash Paid",   inv.get("cash_paid",   0))
        _prow("Card Paid",   inv.get("card_paid",   0))
        if inv.get("card_details"):
            pl.addLayout(_kv_row("Card Details", inv.get("card_details", "")))
        _prow("Cheque Paid", inv.get("cheque_paid", 0))
        if inv.get("cheque_details"):
            pl.addLayout(_kv_row("Cheque Details", inv.get("cheque_details", "")))
        _prow("UPI Paid",    inv.get("upi_paid",    0))
        _prow("Due Amount",  inv.get("due_amount",  0))
        if inv.get("due_date"):
            pl.addLayout(_kv_row("Due Date", inv.get("due_date", "")))
        if inv.get("remarks"):
            pl.addLayout(_kv_row("Remarks",  inv.get("remarks",  "")))
        pl.addStretch()
        pt_row.addWidget(pay_grp, 3)

        # Tax & Grand Total
        tax_grp, tl = _card("Tax & Total")

        def _trow(label, val, bold=False, color=None):
            row = QHBoxLayout()
            lk = QLabel(label + ":")
            lk.setStyleSheet(f"color:#7f8c8d;font-size:12px;{'font-weight:bold;' if bold else ''}")
            lk.setFixedWidth(140)
            lv = QLabel(str(val))
            style = f"font-size:12px;{'font-weight:bold;' if bold else ''}"
            if color:
                style += f"color:{color};"
            lv.setStyleSheet(style)
            lv.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(lk)
            row.addWidget(lv, 1)
            return row

        subtotal = float(inv.get("subtotal",    0))
        cgst_pct = float(inv.get("cgst_percent", 0))
        sgst_pct = float(inv.get("sgst_percent", 0))
        igst_pct = float(inv.get("igst_percent", 0))
        cgst_amt = float(inv.get("cgst_amount",  round(subtotal * cgst_pct / 100, 2)))
        sgst_amt = float(inv.get("sgst_amount",  round(subtotal * sgst_pct / 100, 2)))
        igst_amt = float(inv.get("igst_amount",  round(subtotal * igst_pct / 100, 2)))
        grand    = float(inv.get("grand_total",  0))

        tl.addLayout(_trow("Gross Amount",        format_currency(subtotal)))
        tl.addLayout(_trow(f"CGST ({cgst_pct}%)", format_currency(cgst_amt)))
        tl.addLayout(_trow(f"SGST ({sgst_pct}%)", format_currency(sgst_amt)))
        if igst_pct or igst_amt:
            tl.addLayout(_trow(f"IGST ({igst_pct}%)", format_currency(igst_amt)))

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color:#e0e0e0;")
        tl.addWidget(sep2)
        tl.addLayout(_trow("NET PAYABLE", format_currency(grand), bold=True, color="#27ae60"))
        tl.addStretch()
        pt_row.addWidget(tax_grp, 2)

        root.addLayout(pt_row)

        # Notes
        if inv.get("notes"):
            notes_grp, nl = _card("Notes")
            nl.addWidget(QLabel(inv.get("notes", "")))
            root.addWidget(notes_grp)

        # ── Footer buttons ─────────────────────────────────────
        foot = QFrame()
        foot.setStyleSheet("background:white; border-top:1px solid #e0e0e0;")
        foot.setFixedHeight(56)
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(18, 8, 18, 8)

        btn_preview = QPushButton("👁  Preview PDF")
        btn_preview.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;border-radius:5px;"
            "padding:9px 20px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#7d3c98;}"
        )
        btn_preview.clicked.connect(self._preview_pdf)

        btn_pdf = QPushButton("🖨  Download PDF")
        btn_pdf.setStyleSheet(
            "QPushButton{background:#f39c12;color:white;border-radius:5px;"
            "padding:9px 20px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#e67e22;}"
        )
        btn_pdf.clicked.connect(self._download_pdf)

        btn_dup = QPushButton("📋  Duplicate")
        btn_dup.setToolTip("Open a new invoice pre-filled with this invoice's data")
        btn_dup.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;border-radius:5px;"
            "padding:9px 20px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#7d3c98;}"
        )
        btn_dup.clicked.connect(self._duplicate)

        btn_edit = QPushButton("✏️  Edit Invoice")
        btn_edit.setToolTip("Edit and update this saved invoice")
        btn_edit.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:5px;"
            "padding:9px 20px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        btn_edit.clicked.connect(self._edit)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet(
            "QPushButton{background:#7f8c8d;color:white;border-radius:5px;"
            "padding:9px 20px;border:none;}"
            "QPushButton:hover{background:#95a5a6;}"
        )
        btn_close.clicked.connect(self.accept)

        fl.addStretch()
        fl.addWidget(btn_preview)
        fl.addWidget(btn_pdf)
        fl.addWidget(btn_dup)
        fl.addWidget(btn_edit)
        fl.addWidget(btn_close)
        outer.addWidget(foot)

    def _edit(self):
        if self._on_edit:
            self._on_edit(self._invoice)
            self.accept()

    def _duplicate(self):
        if self._on_duplicate:
            self._on_duplicate(self._invoice)
            self.accept()

    def _preview_pdf(self):
        from ui.invoice_preview_dialog import InvoicePreviewDialog
        InvoicePreviewDialog(self._invoice, parent=self).exec()

    def _download_pdf(self):
        from app.printer_helper import save_invoice_as_pdf
        save_invoice_as_pdf(self._invoice, parent=self)
