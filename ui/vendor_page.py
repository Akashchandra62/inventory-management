# ui/vendor_page.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QFormLayout, QGroupBox, QFrame, QHeaderView,
    QAbstractItemView, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.vendor_service import get_all_vendors, add_vendor, update_vendor, delete_vendor
from models.vendor_model import VendorModel


class VendorDialog(QDialog):
    def __init__(self, parent=None, vendor: dict = None):
        super().__init__(parent)
        self.vendor = vendor
        self.setWindowTitle("Edit Vendor" if vendor else "Add Vendor")
        self.setMinimumWidth(460)
        self._build_ui()
        if vendor: self._populate(vendor)

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(20,20,20,20); root.setSpacing(12)
        grp = QGroupBox("Vendor Details")
        form = QFormLayout(grp); form.setSpacing(8); form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def le(ph=""): e = QLineEdit(); e.setPlaceholderText(ph); e.setMinimumHeight(32); return e
        self.txt_name  = le("Vendor/company name *")
        self.txt_phone = le("Phone number")
        self.txt_addr  = le("Full address")
        self.txt_gst   = le("GST number (optional)")
        self.txt_email = le("Email (optional)")
        self.txt_notes = QTextEdit(); self.txt_notes.setPlaceholderText("Notes..."); self.txt_notes.setMaximumHeight(80)

        form.addRow("Name *",   self.txt_name)
        form.addRow("Phone",    self.txt_phone)
        form.addRow("Address",  self.txt_addr)
        form.addRow("GST No",   self.txt_gst)
        form.addRow("Email",    self.txt_email)
        form.addRow("Notes",    self.txt_notes)
        root.addWidget(grp)

        br = QHBoxLayout(); br.addStretch()
        btn_s = QPushButton("💾  Save"); btn_s.setStyleSheet("background:#27ae60;color:white;border-radius:4px;padding:8px 20px;"); btn_s.clicked.connect(self._save)
        btn_c = QPushButton("Cancel"); btn_c.setStyleSheet("background:#7f8c8d;color:white;border-radius:4px;padding:8px 16px;"); btn_c.clicked.connect(self.reject)
        br.addWidget(btn_s); br.addWidget(btn_c); root.addLayout(br)

    def _populate(self, v: dict):
        self.txt_name.setText(v.get("vendor_name",""))
        self.txt_phone.setText(v.get("phone",""))
        self.txt_addr.setText(v.get("address",""))
        self.txt_gst.setText(v.get("gst_number",""))
        self.txt_email.setText(v.get("email",""))
        self.txt_notes.setText(v.get("notes",""))

    def _save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Vendor name is required."); return
        self.result_data = {
            "vendor_name": self.txt_name.text().strip(),
            "phone":       self.txt_phone.text().strip(),
            "address":     self.txt_addr.text().strip(),
            "gst_number":  self.txt_gst.text().strip(),
            "email":       self.txt_email.text().strip(),
            "notes":       self.txt_notes.toPlainText().strip(),
        }
        self.accept()


class VendorPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(scroll)
        container = QWidget(); scroll.setWidget(container)
        root = QVBoxLayout(container); root.setContentsMargins(25,20,25,20); root.setSpacing(14)

        top = QHBoxLayout()
        title = QLabel("🏪  Vendor Management"); title.setFont(QFont("Segoe UI",16,QFont.Weight.Bold))
        btn_add = QPushButton("➕  Add Vendor"); btn_add.setStyleSheet("background:#27ae60;color:white;border-radius:4px;padding:8px 16px;"); btn_add.clicked.connect(self._add)
        top.addWidget(title); top.addStretch(); top.addWidget(btn_add); root.addLayout(top)

        sr = QHBoxLayout()
        self.txt_s = QLineEdit(); self.txt_s.setPlaceholderText("Search vendors..."); self.txt_s.setMinimumHeight(34); self.txt_s.textChanged.connect(self._search)
        sr.addWidget(QLabel("🔍")); sr.addWidget(self.txt_s); root.addLayout(sr)

        self.tbl = QTableWidget(); self.tbl.setColumnCount(7)
        self.tbl.setHorizontalHeaderLabels(["ID","Name","Phone","Address","GST","Email","Notes"])
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setAlternatingRowColors(True); self.tbl.setMinimumHeight(360)
        root.addWidget(self.tbl)

        act = QHBoxLayout(); act.addStretch()
        btn_e = QPushButton("✏️  Edit"); btn_e.setStyleSheet("background:#2980b9;color:white;border-radius:4px;padding:8px 16px;"); btn_e.clicked.connect(self._edit)
        btn_d = QPushButton("🗑  Delete"); btn_d.setStyleSheet("background:#e74c3c;color:white;border-radius:4px;padding:8px 16px;"); btn_d.clicked.connect(self._delete)
        act.addWidget(btn_e); act.addWidget(btn_d); root.addLayout(act)
        self._all: list = []

    def refresh(self):
        self._all = get_all_vendors(); self._populate(self._all)

    def _search(self, text):
        q = text.lower()
        self._populate([v for v in self._all if q in v.get("vendor_name","").lower() or q in v.get("phone","")])

    def _populate(self, data):
        self.tbl.setRowCount(0)
        for v in data:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            for c, key in enumerate(["vendor_id","vendor_name","phone","address","gst_number","email","notes"]):
                cell = QTableWidgetItem(str(v.get(key,""))); cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(r,c,cell)
        self.tbl.setColumnHidden(0,True)

    def _add(self):
        dlg = VendorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            add_vendor(VendorModel(**dlg.result_data)); self.refresh()

    def _edit(self):
        row = self.tbl.currentRow()
        if row < 0: QMessageBox.information(self,"Edit","Select a row."); return
        vid = self.tbl.item(row,0).text()
        v   = next((x for x in self._all if x.get("vendor_id")==vid), None)
        if not v: return
        dlg = VendorDialog(self, vendor=v)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            update_vendor(vid, dlg.result_data); self.refresh()

    def _delete(self):
        row = self.tbl.currentRow()
        if row < 0: QMessageBox.information(self,"Delete","Select a row."); return
        vid  = self.tbl.item(row,0).text()
        name = self.tbl.item(row,1).text()
        if QMessageBox.question(self,"Delete",f"Delete vendor '{name}'?",
                                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            delete_vendor(vid); self.refresh()
