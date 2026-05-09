# ui/customer_page.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QFrame, QHeaderView, QAbstractItemView, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from services.customer_service import get_all_customers, delete_customer
from services.invoice_service import get_all_invoices
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf, preview_invoice_pdf


_C_HEADERS  = ["ID", "Name ▲▼", "Mobile ▲▼", "Address ▲▼", "Email ▲▼"]
_C_LABELS   = ["ID", "Name", "Mobile", "Address", "Email"]   # base labels (no indicator)
_C_KEYS     = ["customer_id", "customer_name", "mobile", "address", "email"]
_I_HEADERS  = ["Invoice No ▲▼", "Date ▲▼", "Items ▲▼", "Tax ▲▼", "Grand Total ▲▼", "Due Amount ▲▼", "Action"]
_I_LABELS   = ["Invoice No", "Date", "Items", "Tax", "Grand Total", "Due Amount", "Action"]
# col → invoice key (col 2 = item count is handled specially)
_I_SORT_KEYS = {0: "invoice_number", 1: "date", 3: "tax_amount", 4: "grand_total", 5: "due_amount"}


class CustomerPage(QWidget):
    def __init__(self):
        super().__init__()
        # Sort state for customers table
        self._c_sort_col = -1;  self._c_sort_asc = True
        # Sort state for invoice history table
        self._i_sort_col = -1;  self._i_sort_asc = True
        self._view_c: list[dict] = []   # current filtered customers (unsorted)
        self._view_i: list[dict] = []   # current customer's invoices (unsorted)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(scroll)
        container = QWidget(); scroll.setWidget(container)
        root = QVBoxLayout(container); root.setContentsMargins(25,20,25,20); root.setSpacing(14)

        title = QLabel("👥  Customer Management"); title.setFont(QFont("Segoe UI",16,QFont.Bold))
        root.addWidget(title)

        sr = QHBoxLayout()
        self.txt_s = QLineEdit(); self.txt_s.setPlaceholderText("Search by name or mobile..."); self.txt_s.setMinimumHeight(34); self.txt_s.textChanged.connect(self._search)
        sr.addWidget(QLabel("🔍")); sr.addWidget(self.txt_s); root.addLayout(sr)

        # Customers table
        clbl = QLabel("Customers  —  click a column header to sort")
        clbl.setStyleSheet("font-weight:bold; color:#555; font-size:11px;")
        root.addWidget(clbl)
        self.tbl_c = QTableWidget(); self.tbl_c.setColumnCount(5)
        self.tbl_c.setHorizontalHeaderLabels(_C_HEADERS)
        hc = self.tbl_c.horizontalHeader()
        hc.setSectionResizeMode(1, QHeaderView.Stretch)
        hc.setCursor(Qt.PointingHandCursor)
        hc.sectionClicked.connect(self._sort_customers)
        self.tbl_c.verticalHeader().setDefaultSectionSize(42)
        self.tbl_c.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_c.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_c.setAlternatingRowColors(True); self.tbl_c.setMaximumHeight(240)
        self.tbl_c.selectionModel().selectionChanged.connect(self._customer_selected)
        root.addWidget(self.tbl_c)

        act = QHBoxLayout(); act.addStretch()
        btn_del = QPushButton("🗑  Delete")
        btn_del.setStyleSheet("background:#e74c3c;color:white;border-radius:4px;padding:8px 16px;")
        btn_del.clicked.connect(self._delete)
        act.addWidget(btn_del); root.addLayout(act)

        # Customer summary bar
        self._frm_summary = QFrame()
        self._frm_summary.setStyleSheet(
            "QFrame{background:#1a3a5c;border-radius:6px;padding:2px;}"
        )
        self._frm_summary.setVisible(False)
        sl = QHBoxLayout(self._frm_summary)
        sl.setContentsMargins(20, 10, 20, 10); sl.setSpacing(0)

        def _sum_card(label, attr, color="#7fb3d3"):
            col = QVBoxLayout(); col.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{color};font-size:10px;font-weight:bold;background:transparent;")
            lbl.setAlignment(Qt.AlignCenter)
            val = QLabel("—")
            val.setStyleSheet("color:white;font-size:13px;font-weight:bold;background:transparent;")
            val.setAlignment(Qt.AlignCenter)
            col.addWidget(lbl); col.addWidget(val)
            setattr(self, attr, val)
            return col

        def _vsep():
            sep = QFrame(); sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet("QFrame{color:#345;background:#345;max-width:1px;}")
            return sep

        sl.addLayout(_sum_card("TOTAL INVOICES",  "lbl_s_count",    "#82e0aa"))
        sl.addWidget(_vsep())
        sl.addLayout(_sum_card("TOTAL PURCHASE",  "lbl_s_purchase",  "#aed6f1"))
        sl.addWidget(_vsep())
        sl.addLayout(_sum_card("TOTAL PAID",      "lbl_s_paid",      "#f9e79f"))
        sl.addWidget(_vsep())
        sl.addLayout(_sum_card("TOTAL DUE",       "lbl_s_due",       "#f1948a"))
        root.addWidget(self._frm_summary)

        # Invoice history
        ilbl = QLabel("Invoice History for Selected Customer  —  click a column header to sort")
        ilbl.setStyleSheet("font-weight:bold; color:#555; font-size:11px;")
        root.addWidget(ilbl)
        self.tbl_i = QTableWidget(); self.tbl_i.setColumnCount(7)
        self.tbl_i.setHorizontalHeaderLabels(_I_HEADERS)
        hi = self.tbl_i.horizontalHeader()
        hi.setSectionResizeMode(0, QHeaderView.Stretch)
        hi.setCursor(Qt.PointingHandCursor)
        hi.sectionClicked.connect(self._sort_invoices)
        self.tbl_i.verticalHeader().setDefaultSectionSize(42)
        self.tbl_i.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_i.setAlternatingRowColors(True); self.tbl_i.setMinimumHeight(180)
        root.addWidget(self.tbl_i)

        self._all_c = []; self._all_inv = []

    def refresh(self):
        self._all_c = get_all_customers(); self._all_inv = get_all_invoices()
        self._view_c = self._all_c
        self._populate_customers(self._apply_c_sort(self._view_c))

    def _search(self, text):
        q = text.lower()
        if len(q) < 3 and len(q) > 0: return
        self._view_c = [
            c for c in self._all_c
            if q in f"{c.get('customer_name','')} {c.get('mobile','')} "
                    f"{c.get('email','')} {c.get('address','')}".lower()
        ]
        self._populate_customers(self._apply_c_sort(self._view_c))

    def _populate_customers(self, data):
        self.tbl_c.setRowCount(0); self.tbl_i.setRowCount(0)
        self._frm_summary.setVisible(False)
        for c in data:
            r = self.tbl_c.rowCount(); self.tbl_c.insertRow(r)
            for col, key in enumerate(_C_KEYS):
                cell = QTableWidgetItem(str(c.get(key, "")))
                cell.setTextAlignment(Qt.AlignCenter)
                self.tbl_c.setItem(r, col, cell)
        self.tbl_c.setColumnHidden(0, True)

    # kept for backward-compat calls
    def _populate(self, data):
        self._view_c = data
        self._populate_customers(self._apply_c_sort(data))

    def _customer_selected(self):
        row = self.tbl_c.currentRow()
        if row < 0:
            self._view_i = []
            self.tbl_i.setRowCount(0)
            self._frm_summary.setVisible(False)
            return
        mobile = self.tbl_c.item(row, 2).text() if self.tbl_c.item(row, 2) else ""
        name   = self.tbl_c.item(row, 1).text() if self.tbl_c.item(row, 1) else ""
        self._view_i = [i for i in self._all_inv if
                        (mobile and i.get("customer_mobile", "") == mobile) or
                        (name and i.get("customer_name", "").lower() == name.lower())]
        self._i_sort_col = -1; self._i_sort_asc = True
        self._refresh_i_headers()
        self._populate_invoices(self._view_i)
        self._update_summary(self._view_i)

    def _update_summary(self, invoices):
        total_purchase = sum(float(i.get("grand_total", 0) or 0) for i in invoices)
        total_due      = sum(float(i.get("due_amount",   0) or 0) for i in invoices)
        total_paid     = total_purchase - total_due

        self.lbl_s_count.setText(str(len(invoices)))
        self.lbl_s_purchase.setText(f"₹ {total_purchase:,.2f}")
        self.lbl_s_paid.setText(f"₹ {total_paid:,.2f}")
        self.lbl_s_due.setText(f"₹ {total_due:,.2f}")

        due_color = "#e74c3c" if total_due > 0 else "#82e0aa"
        self.lbl_s_due.setStyleSheet(
            f"color:{due_color};font-size:13px;font-weight:bold;background:transparent;"
        )
        self._frm_summary.setVisible(True)

    # ── Customer table sort ───────────────────────────────────
    def _sort_customers(self, col: int):
        if col == 0:   # ID column hidden — skip
            return
        if self._c_sort_col == col:
            if not self._c_sort_asc:        # desc → asc
                self._c_sort_asc = True
            else:                           # asc → remove sort
                self._c_sort_col = -1
                self._refresh_c_headers()
                self._populate_customers(self._view_c)
                return
        else:
            self._c_sort_col = col
            self._c_sort_asc = False        # first click → descending
        self._refresh_c_headers()
        self._populate_customers(self._apply_c_sort(self._view_c))

    def _apply_c_sort(self, data: list) -> list:
        if self._c_sort_col < 0 or self._c_sort_col >= len(_C_KEYS):
            return list(data)
        key = _C_KEYS[self._c_sort_col]
        return sorted(data, key=lambda c: str(c.get(key, "")).lower(),
                      reverse=not self._c_sort_asc)

    def _refresh_c_headers(self):
        for i, lbl in enumerate(_C_LABELS):
            item = self.tbl_c.horizontalHeaderItem(i)
            if item:
                if i == self._c_sort_col:
                    item.setText(lbl + (" ▲" if self._c_sort_asc else " ▼"))
                elif i == 0:
                    item.setText(lbl)       # ID column — no sort indicator
                else:
                    item.setText(lbl + " ▲▼")

    # ── Invoice history sort ──────────────────────────────────
    def _sort_invoices(self, col: int):
        if col == 6:   # Action column — not sortable
            return
        if self._i_sort_col == col:
            if not self._i_sort_asc:        # desc → asc
                self._i_sort_asc = True
            else:                           # asc → remove sort
                self._i_sort_col = -1
                self._refresh_i_headers()
                self._populate_invoices(self._view_i)
                return
        else:
            self._i_sort_col = col
            self._i_sort_asc = False        # first click → descending
        self._refresh_i_headers()
        self._populate_invoices(self._apply_i_sort(self._view_i))

    def _apply_i_sort(self, data: list) -> list:
        if self._i_sort_col < 0:
            return list(data)
        if self._i_sort_col == 2:   # Items column = count
            return sorted(data, key=lambda i: len(i.get("items", [])),
                          reverse=not self._i_sort_asc)
        if self._i_sort_col not in _I_SORT_KEYS:
            return list(data)
        key = _I_SORT_KEYS[self._i_sort_col]
        def _k(inv):
            v = inv.get(key, "")
            try:    return (0, float(v))
            except: return (1, str(v).lower())
        return sorted(data, key=_k, reverse=not self._i_sort_asc)

    def _refresh_i_headers(self):
        for i, lbl in enumerate(_I_LABELS):
            item = self.tbl_i.horizontalHeaderItem(i)
            if item:
                if i == self._i_sort_col:
                    item.setText(lbl + (" ▲" if self._i_sort_asc else " ▼"))
                elif i == 6:
                    item.setText(lbl)       # Action column — no sort indicator
                else:
                    item.setText(lbl + " ▲▼")

    # ── Invoice history population ────────────────────────────
    def _populate_invoices(self, invoices: list):
        self.tbl_i.setRowCount(0)
        for inv in invoices:
            r = self.tbl_i.rowCount(); self.tbl_i.insertRow(r)
            due = float(inv.get("due_amount", 0) or 0)
            vals = [inv.get("invoice_number",""), inv.get("date",""),
                    str(len(inv.get("items",[]))),
                    format_currency(inv.get("tax_amount", 0)),
                    format_currency(inv.get("grand_total", 0)),
                    format_currency(due)]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v); cell.setTextAlignment(Qt.AlignCenter)
                if c == 5 and due > 0:
                    cell.setForeground(QColor("#c0392b"))
                    f = cell.font(); f.setBold(True); cell.setFont(f)
                self.tbl_i.setItem(r, c, cell)
            btn_prev = QPushButton("Preview")
            btn_prev.setStyleSheet("background:#8e44ad; color:white; padding: 4px 8px; border-radius:3px; font-weight:bold; font-size:11px;")
            btn_prev.clicked.connect(lambda checked, i=inv: preview_invoice_pdf(i, parent=self))
            btn_dl = QPushButton("Download")
            btn_dl.setStyleSheet("background:#27ae60; color:white; padding: 4px 8px; border-radius:3px; font-weight:bold; font-size:11px;")
            btn_dl.clicked.connect(lambda checked, i=inv: save_invoice_as_pdf(i, parent=self))
            btn_container = QWidget(); bl = QHBoxLayout(btn_container)
            bl.setContentsMargins(2, 0, 2, 0); bl.setSpacing(4); bl.setAlignment(Qt.AlignCenter)
            bl.addWidget(btn_prev); bl.addWidget(btn_dl)
            self.tbl_i.setCellWidget(r, 6, btn_container)

    def _delete(self):
        row = self.tbl_c.currentRow()
        if row < 0: QMessageBox.information(self,"Delete","Select a customer."); return
        cid  = self.tbl_c.item(row,0).text()
        name = self.tbl_c.item(row,1).text()
        if QMessageBox.question(self,"Delete",f"Delete customer '{name}'?",
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            delete_customer(cid); self.refresh()
