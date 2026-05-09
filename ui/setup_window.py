# ============================================================
# ui/setup_window.py - First-Time Shop Setup
# ============================================================

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QPushButton,
    QFormLayout, QGroupBox, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from app.config import AppConfig
from app.utils import safe_float


class SetupWindow(QDialog):
    """One-time shop details + credentials setup dialog (shown on first launch)."""

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
        hdr.setFont(QFont("Segoe UI", 15, QFont.Bold))
        hdr.setStyleSheet("color: #2c3e50;")
        sub = QLabel("Set up your shop details and login credentials to get started.")
        sub.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        root.addWidget(hdr)
        root.addWidget(sub)

        # ── Shop Information ──────────────────────────────────
        grp_shop = QGroupBox("Shop Information")
        form = QFormLayout(grp_shop)
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        def field(placeholder=""):
            le = QLineEdit()
            le.setPlaceholderText(placeholder)
            le.setMinimumHeight(34)
            return le

        self.txt_shop    = field("e.g. Lakshmi Jewellers")
        self.txt_owner   = field("Owner / Proprietor name")
        self.txt_address = field("Full shop address")
        self.txt_mobile  = field("10-digit mobile")
        self.txt_gst     = field("15-char GST number (optional)")
        self.txt_email   = field("shop@email.com (optional)")
        self.txt_prefix  = field("e.g. JB")
        self.txt_prefix.setText("JB")

        self.spn_tax = QDoubleSpinBox()
        self.spn_tax.setRange(0, 28)
        self.spn_tax.setValue(3.0)
        self.spn_tax.setSuffix(" %")
        self.spn_tax.setMinimumHeight(34)

        form.addRow("Shop Name *",     self.txt_shop)
        form.addRow("Owner Name *",    self.txt_owner)
        form.addRow("Address *",       self.txt_address)
        form.addRow("Mobile *",        self.txt_mobile)
        form.addRow("GST Number",      self.txt_gst)
        form.addRow("Email",           self.txt_email)
        form.addRow("Invoice Prefix *",self.txt_prefix)
        form.addRow("Default Tax",     self.spn_tax)
        root.addWidget(grp_shop)

        # ── Login Credentials ─────────────────────────────────
        grp_cred = QGroupBox("Login Credentials")
        grp_cred.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #2c3e50; "
            "border: 1px solid #f39c12; border-radius: 5px; margin-top: 8px; padding-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; background: white; }"
        )
        cform = QFormLayout(grp_cred)
        cform.setLabelAlignment(Qt.AlignRight)
        cform.setSpacing(10)

        self.txt_username = field("Username (e.g. admin)")
        self.txt_username.setText("admin")

        self.txt_password  = QLineEdit()
        self.txt_password.setPlaceholderText("Choose a password")
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setMinimumHeight(34)

        self.txt_confirm = QLineEdit()
        self.txt_confirm.setPlaceholderText("Re-enter password")
        self.txt_confirm.setEchoMode(QLineEdit.Password)
        self.txt_confirm.setMinimumHeight(34)

        # Eye-toggle buttons
        def _add_eye(pwd_field):
            row = QHBoxLayout()
            row.setSpacing(4)
            row.addWidget(pwd_field)
            btn = QPushButton("👁")
            btn.setFixedSize(34, 34)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton { border: 1px solid #ced4da; border-radius: 4px; background: #f8f9fa; }"
                "QPushButton:checked { background: #d5e8f7; }"
            )
            btn.toggled.connect(
                lambda checked, f=pwd_field: f.setEchoMode(
                    QLineEdit.Normal if checked else QLineEdit.Password
                )
            )
            row.addWidget(btn)
            return row

        cform.addRow("Username *",         self.txt_username)
        cform.addRow("Password *",         _add_eye(self.txt_password))
        cform.addRow("Confirm Password *", _add_eye(self.txt_confirm))

        note = QLabel("These credentials will be used to log in to the app every time.")
        note.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        note.setWordWrap(True)
        cform.addRow("", note)

        root.addWidget(grp_cred)

        # ── Save button ───────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = QPushButton("Save & Continue")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.setStyleSheet(
            "QPushButton { background:#f39c12; color:white; border-radius:5px;"
            " font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#e67e22; }"
        )
        self.btn_save.clicked.connect(self._save)
        btn_row.addWidget(self.btn_save)
        root.addLayout(btn_row)

    def _save(self):
        # ── Validate shop fields ──────────────────────────────
        shop_name  = self.txt_shop.text().strip()
        owner_name = self.txt_owner.text().strip()
        address    = self.txt_address.text().strip()
        mobile     = self.txt_mobile.text().strip()
        prefix     = self.txt_prefix.text().strip()

        if not shop_name:
            QMessageBox.warning(self, "Validation", "Shop Name is required.")
            self.txt_shop.setFocus(); return
        if not owner_name:
            QMessageBox.warning(self, "Validation", "Owner Name is required.")
            self.txt_owner.setFocus(); return
        if not address:
            QMessageBox.warning(self, "Validation", "Address is required.")
            self.txt_address.setFocus(); return
        if not mobile:
            QMessageBox.warning(self, "Validation", "Mobile is required.")
            self.txt_mobile.setFocus(); return
        if not prefix:
            QMessageBox.warning(self, "Validation", "Invoice Prefix is required.")
            self.txt_prefix.setFocus(); return

        # ── Validate credentials ──────────────────────────────
        username = self.txt_username.text().strip()
        password = self.txt_password.text()
        confirm  = self.txt_confirm.text()

        if not username:
            QMessageBox.warning(self, "Validation", "Username is required.")
            self.txt_username.setFocus(); return
        if not password:
            QMessageBox.warning(self, "Validation", "Password is required.")
            self.txt_password.setFocus(); return
        if len(password) < 4:
            QMessageBox.warning(self, "Validation", "Password must be at least 4 characters.")
            self.txt_password.setFocus(); return
        if password != confirm:
            QMessageBox.warning(self, "Validation", "Passwords do not match.")
            self.txt_confirm.setFocus(); return

        # ── Save shop details ─────────────────────────────────
        shop_data = {
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
        if not AppConfig.save_shop(shop_data):
            QMessageBox.critical(self, "Error", "Failed to save shop details. Check file permissions.")
            return

        # ── Save credentials ──────────────────────────────────
        from app.database import get_db
        try:
            with get_db() as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    [("username", username), ("password", password)],
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save credentials:\n{e}")
            return

        AppConfig.load()
        QMessageBox.information(
            self, "Setup Complete",
            f"Setup complete!\n\nUsername: {username}\n\nYou can now log in."
        )
        self.accept()
