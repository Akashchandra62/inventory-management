# ============================================================
# ui/setup_window.py - First-Time Shop Setup
# ============================================================

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QPushButton,
    QFormLayout, QGroupBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from app.config import AppConfig
from app.utils import safe_float


class SetupWindow(QDialog):
    """One-time shop details setup dialog (shown on first launch)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First-Time Setup – Shop Details")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(30, 25, 30, 25)

        # Header
        hdr = QLabel("💎  Welcome to Jewelry Billing System")
        hdr.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        hdr.setStyleSheet("color: #2c3e50;")
        sub = QLabel("Please enter your shop details to get started.")
        sub.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        root.addWidget(hdr)
        root.addWidget(sub)

        # Form
        grp = QGroupBox("Shop Information")
        form = QFormLayout(grp)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)

        def field(placeholder=""):
            le = QLineEdit()
            le.setPlaceholderText(placeholder)
            le.setMinimumHeight(34)
            return le

        self.txt_shop     = field("e.g. Lakshmi Jewellers")
        self.txt_owner    = field("Owner / Proprietor name")
        self.txt_address  = field("Full shop address")
        self.txt_mobile   = field("10-digit mobile")
        self.txt_gst      = field("15-char GST number (optional)")
        self.txt_email    = field("shop@email.com (optional)")
        self.txt_prefix   = field("e.g. JB")
        self.txt_prefix.setText("JB")

        self.spn_tax = QDoubleSpinBox()
        self.spn_tax.setRange(0, 28)
        self.spn_tax.setValue(3.0)
        self.spn_tax.setSuffix(" %")
        self.spn_tax.setMinimumHeight(34)

        form.addRow("Shop Name *", self.txt_shop)
        form.addRow("Owner Name *", self.txt_owner)
        form.addRow("Address *", self.txt_address)
        form.addRow("Mobile *", self.txt_mobile)
        form.addRow("GST Number", self.txt_gst)
        form.addRow("Email", self.txt_email)
        form.addRow("Invoice Prefix *", self.txt_prefix)
        form.addRow("Default Tax", self.spn_tax)
        root.addWidget(grp)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = QPushButton("Save & Continue")
        self.btn_save.setObjectName("btn_primary")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.setStyleSheet(
            "QPushButton { background:#f39c12; color:white; border-radius:5px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#e67e22; }"
        )
        self.btn_save.clicked.connect(self._save)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

    def _save(self):
        shop_name  = self.txt_shop.text().strip()
        owner_name = self.txt_owner.text().strip()
        address    = self.txt_address.text().strip()
        mobile     = self.txt_mobile.text().strip()
        prefix     = self.txt_prefix.text().strip()

        if not shop_name:
            QMessageBox.warning(self, "Validation", "Shop Name is required.")
            return
        if not owner_name:
            QMessageBox.warning(self, "Validation", "Owner Name is required.")
            return
        if not address:
            QMessageBox.warning(self, "Validation", "Address is required.")
            return
        if not mobile:
            QMessageBox.warning(self, "Validation", "Mobile is required.")
            return
        if not prefix:
            QMessageBox.warning(self, "Validation", "Invoice Prefix is required.")
            return

        data = {
            "shop_name":      shop_name,
            "owner_name":     owner_name,
            "address":        address,
            "mobile":         mobile,
            "gst_number":     self.txt_gst.text().strip(),
            "email":          self.txt_email.text().strip(),
            "invoice_prefix": prefix,
            "default_tax":    self.spn_tax.value(),
            "printer":        ""
        }

        if AppConfig.save_shop(data):
            AppConfig.load()
            QMessageBox.information(self, "Setup Complete",
                                    "Shop details saved successfully!\nYou can now login.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save shop details. Check file permissions.")
