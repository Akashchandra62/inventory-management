# ui/customer_page.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QFrame, QHeaderView, QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.customer_service import get_all_customers, delete_customer
from services.invoice_service import get_all_invoices
from app.utils import format_currency
from app.printer_helper import save_invoice_as_pdf


class CustomerPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(scroll)
        container = QWidget(); scroll.setWidget(container)
        root = QVBoxLayout(container); root.setContentsMargins(25,20,25,20); root.setSpacing(14)

        title = QLabel("👥  Customer Management"); title.setFont(QFont("Segoe UI",16,QFont.Weight.Bold))
        root.addWidget(title)

        sr = QHBoxLayout()
        self.txt_s = QLineEdit(); self.txt_s.setPlaceholderText("Search by name or mobile..."); self.txt_s.setMinimumHeight(34); self.txt_s.textChanged.connect(self._search)
        sr.addWidget(QLabel("🔍")); sr.addWidget(self.txt_s); root.addLayout(sr)

        # Customers table
        clbl = QLabel("Customers"); clbl.setStyleSheet("font-weight:bold;")
        root.addWidget(clbl)
        self.tbl_c = QTableWidget(); self.tbl_c.setColumnCount(5)
        self.tbl_c.setHorizontalHeaderLabels(["ID","Name","Mobile","Address","Email"])
        self.tbl_c.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.tbl_c.verticalHeader().setDefaultSectionSize(42)
        self.tbl_c.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_c.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_c.setAlternatingRowColors(True); self.tbl_c.setMaximumHeight(240)
        self.tbl_c.selectionModel().selectionChanged.connect(self._customer_selected)
        root.addWidget(self.tbl_c)

        act = QHBoxLayout(); act.addStretch()
        btn_del = QPushButton("🗑  Delete"); btn_del.setStyleSheet("background:#e74c3c;color:white;border-radius:4px;padding:8px 16px;"); btn_del.clicked.connect(self._delete)
        act.addWidget(btn_del); root.addLayout(act)

        # Invoice history
        ilbl = QLabel("Invoice History for Selected Customer"); ilbl.setStyleSheet("font-weight:bold;")
        root.addWidget(ilbl)
        self.tbl_i = QTableWidget(); self.tbl_i.setColumnCount(6)
        self.tbl_i.setHorizontalHeaderLabels(["Invoice No","Date","Items","Tax","Grand Total", "Action"])
        self.tbl_i.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.tbl_i.verticalHeader().setDefaultSectionSize(42)
        self.tbl_i.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_i.setAlternatingRowColors(True); self.tbl_i.setMinimumHeight(180)
        root.addWidget(self.tbl_i)

        self._all_c = []; self._all_inv = []

    def refresh(self):
        self._all_c = get_all_customers(); self._all_inv = get_all_invoices()
        self._populate(self._all_c)

    def _search(self, text):
        q = text.lower()
        if len(q) < 3 and len(q) > 0: return
        self._populate([c for c in self._all_c if q in f"{c.get('customer_name','')} {c.get('mobile','')} {c.get('email','')} {c.get('address','')}".lower()])

    def _populate(self, data):
        self.tbl_c.setRowCount(0); self.tbl_i.setRowCount(0)
        for c in data:
            r = self.tbl_c.rowCount(); self.tbl_c.insertRow(r)
            for col, key in enumerate(["customer_id","customer_name","mobile","address","email"]):
                cell = QTableWidgetItem(str(c.get(key,""))); cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_c.setItem(r,col,cell)
        self.tbl_c.setColumnHidden(0,True)

    def _customer_selected(self):
        row = self.tbl_c.currentRow()
        if row < 0: self.tbl_i.setRowCount(0); return
        mobile = self.tbl_c.item(row,2).text() if self.tbl_c.item(row,2) else ""
        name   = self.tbl_c.item(row,1).text() if self.tbl_c.item(row,1) else ""
        invs   = [i for i in self._all_inv if
                  (mobile and i.get("customer_mobile","") == mobile) or
                  (name and i.get("customer_name","").lower() == name.lower())]
        self.tbl_i.setRowCount(0)
        for inv in invs:
            r = self.tbl_i.rowCount(); self.tbl_i.insertRow(r)
            vals = [inv.get("invoice_number",""), inv.get("date",""),
                    str(len(inv.get("items",[]))),
                    format_currency(inv.get("tax_amount",0)),
                    format_currency(inv.get("grand_total",0))]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v); cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_i.setItem(r,c,cell)
                
            btn_dl = QPushButton("Download")
            btn_dl.setStyleSheet("background:#27ae60; color:white; padding: 4px 8px; border-radius:3px; font-weight:bold; font-size:11px;")
            btn_dl.clicked.connect(lambda checked, i=inv: save_invoice_as_pdf(i, parent=self))
            btn_container = QWidget(); bl = QHBoxLayout(btn_container); bl.setContentsMargins(0,0,0,0); bl.setAlignment(Qt.AlignmentFlag.AlignCenter); bl.addWidget(btn_dl)
            self.tbl_i.setCellWidget(r, 5, btn_container)

    def _delete(self):
        row = self.tbl_c.currentRow()
        if row < 0: QMessageBox.information(self,"Delete","Select a customer."); return
        cid  = self.tbl_c.item(row,0).text()
        name = self.tbl_c.item(row,1).text()
        if QMessageBox.question(self,"Delete",f"Delete customer '{name}'?",
                                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            delete_customer(cid); self.refresh()
