# ============================================================
# ui/settings_page.py - Full Settings with Logo & QR Upload
# ============================================================

import os
import shutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QGroupBox, QDoubleSpinBox,
    QMessageBox, QFrame, QScrollArea, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from app.config import AppConfig
from app.constants import APP_NAME, APP_VERSION, ASSETS_DIR, LOGO_FILE, QR_FILE


def _ensure_assets_dir():
    os.makedirs(ASSETS_DIR, exist_ok=True)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        root = QVBoxLayout(container)
        root.setContentsMargins(25, 20, 25, 20)
        root.setSpacing(18)

        title = QLabel("⚙️  Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        def le(ph=""):
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setMinimumHeight(34)
            return e

        # ── Shop Details ──────────────────────────────────────
        grp = QGroupBox("Shop Details")
        form = QFormLayout(grp)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_name         = le("Shop name *")
        self.txt_tagline      = le("e.g. Deals In All Type Of Hallmark Jewellery")
        self.txt_owner        = le("Owner / Proprietor name")
        self.txt_addr         = le("Full shop address")
        self.txt_mobile       = le("Primary mobile number")
        self.txt_mobile2      = le("Second mobile number (optional)")
        self.txt_gst          = le("GST number (e.g. 10ABCDE1234F1Z5)")
        self.txt_email        = le("Email address (optional)")
        self.txt_state        = le("e.g. Bihar Code : 10")
        self.txt_jurisdiction = le("e.g. ROHTAS")
        self.txt_prefix       = le("Invoice prefix e.g. JB")
        self.txt_categories   = le("Comma separated: Gold, Silver, Diamond...")

        form.addRow("Shop Name *",         self.txt_name)
        form.addRow("Tagline",             self.txt_tagline)
        form.addRow("Owner Name",          self.txt_owner)
        form.addRow("Address *",           self.txt_addr)
        form.addRow("Mobile *",            self.txt_mobile)
        form.addRow("Mobile 2",            self.txt_mobile2)
        form.addRow("GST Number",          self.txt_gst)
        form.addRow("Email",               self.txt_email)
        form.addRow("State (for invoice)", self.txt_state)
        form.addRow("Jurisdiction",        self.txt_jurisdiction)
        form.addRow("Invoice Prefix",      self.txt_prefix)
        root.addWidget(grp)

        # ── Item Categories ───────────────────────────────────
        cat_grp = QGroupBox("Manage Categories (used in invoices and stock)")
        cat_form = QFormLayout(cat_grp)
        cat_form.setSpacing(8)
        cat_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        cat_form.addRow("Item Categories", self.txt_categories)
        root.addWidget(cat_grp)

        # ── Bank Details ──────────────────────────────────────
        bank_grp = QGroupBox("Bank Details (printed on every invoice)")
        bank_form = QFormLayout(bank_grp)
        bank_form.setSpacing(8)
        bank_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.txt_bank_name = le("e.g. HDFC BANK")
        self.txt_acc_name  = le("Account holder name")
        self.txt_acc_no    = le("Account number")
        self.txt_branch    = le("Branch name and location")
        self.txt_ifsc      = le("IFSC code e.g. HDFC0002052")

        bank_form.addRow("Bank Name",    self.txt_bank_name)
        bank_form.addRow("Account Name", self.txt_acc_name)
        bank_form.addRow("Account No.",  self.txt_acc_no)
        bank_form.addRow("Branch",       self.txt_branch)
        bank_form.addRow("IFSC Code",    self.txt_ifsc)
        root.addWidget(bank_grp)

        # ── Logo Upload ───────────────────────────────────────
        logo_grp = QGroupBox("Shop Logo (shown on invoice header next to shop name)")
        logo_layout = QHBoxLayout(logo_grp)
        logo_layout.setSpacing(16)

        self.lbl_logo_preview = QLabel("No logo\nuploaded")
        self.lbl_logo_preview.setFixedSize(100, 100)
        self.lbl_logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo_preview.setStyleSheet(
            "border: 2px dashed #bdc3c7; border-radius: 6px;"
            "color: #7f8c8d; font-size: 11px;"
        )

        logo_btn_col = QVBoxLayout()
        btn_upload_logo = QPushButton("📁  Upload Logo")
        btn_upload_logo.setStyleSheet(
            "QPushButton { background:#2980b9; color:white; border-radius:5px; padding:8px 16px; }"
            "QPushButton:hover { background:#2471a3; }"
        )
        btn_upload_logo.clicked.connect(self._upload_logo)

        btn_remove_logo = QPushButton("🗑  Remove Logo")
        btn_remove_logo.setStyleSheet(
            "QPushButton { background:#e74c3c; color:white; border-radius:5px; padding:8px 16px; }"
            "QPushButton:hover { background:#c0392b; }"
        )
        btn_remove_logo.clicked.connect(self._remove_logo)

        logo_note = QLabel("Accepted: PNG, JPG\nRecommended: square image")
        logo_note.setStyleSheet("color: #7f8c8d; font-size: 11px;")

        logo_btn_col.addWidget(btn_upload_logo)
        logo_btn_col.addWidget(btn_remove_logo)
        logo_btn_col.addWidget(logo_note)
        logo_btn_col.addStretch()

        logo_layout.addWidget(self.lbl_logo_preview)
        logo_layout.addLayout(logo_btn_col)
        logo_layout.addStretch()
        root.addWidget(logo_grp)

        # ── QR Code Upload ────────────────────────────────────
        qr_grp = QGroupBox("Payment QR Code (customer scans this on invoice to pay)")
        qr_layout = QHBoxLayout(qr_grp)
        qr_layout.setSpacing(16)

        self.lbl_qr_preview = QLabel("No QR code\nuploaded")
        self.lbl_qr_preview.setFixedSize(120, 120)
        self.lbl_qr_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr_preview.setStyleSheet(
            "border: 2px dashed #bdc3c7; border-radius: 6px;"
            "color: #7f8c8d; font-size: 11px;"
        )

        qr_btn_col = QVBoxLayout()
        btn_upload_qr = QPushButton("📁  Upload QR Code Image")
        btn_upload_qr.setStyleSheet(
            "QPushButton { background:#27ae60; color:white; border-radius:5px; padding:8px 16px; }"
            "QPushButton:hover { background:#229954; }"
        )
        btn_upload_qr.clicked.connect(self._upload_qr)

        btn_remove_qr = QPushButton("🗑  Remove QR Code")
        btn_remove_qr.setStyleSheet(
            "QPushButton { background:#e74c3c; color:white; border-radius:5px; padding:8px 16px; }"
            "QPushButton:hover { background:#c0392b; }"
        )
        btn_remove_qr.clicked.connect(self._remove_qr)

        qr_note = QLabel(
            "Download your QR from PhonePe / Google Pay /\n"
            "Paytm / Bank app and upload it here.\n"
            "It will appear on every invoice automatically."
        )
        qr_note.setStyleSheet("color: #7f8c8d; font-size: 11px;")

        qr_btn_col.addWidget(btn_upload_qr)
        qr_btn_col.addWidget(btn_remove_qr)
        qr_btn_col.addWidget(qr_note)
        qr_btn_col.addStretch()

        qr_layout.addWidget(self.lbl_qr_preview)
        qr_layout.addLayout(qr_btn_col)
        qr_layout.addStretch()
        root.addWidget(qr_grp)

        # ── Terms & Conditions ────────────────────────────────
        terms_grp = QGroupBox("Terms & Conditions (printed on every invoice)")
        terms_layout = QVBoxLayout(terms_grp)
        self.txt_terms = QTextEdit()
        self.txt_terms.setPlaceholderText(
            "Enter each condition on a new line. Example:\n"
            "1. सन देन के समय रसीद लेना आवश्यक है।\n"
            "2. ऑर्डर देने के समय 70% जमा देना अनिवार्य है।\n"
            "3. ऑर्डर की वस्तु रद किसी भी परिस्थिति में नहीं होगी।\n"
            "4. चोरी पतीना से काम हो सकता है।\n"
            "5. जेवर टूटने फूटने के लिए गारंटी नहीं है।"
        )
        self.txt_terms.setMinimumHeight(130)
        terms_layout.addWidget(self.txt_terms)
        root.addWidget(terms_grp)

        # ── Save Button ───────────────────────────────────────
        btn_save = QPushButton("💾  Save All Settings")
        btn_save.setStyleSheet(
            "QPushButton { background:#f39c12; color:white; border-radius:5px;"
            "padding:10px 24px; font-weight:bold; font-size:13px; }"
            "QPushButton:hover { background:#e67e22; }"
        )
        btn_save.setMaximumWidth(240)
        btn_save.clicked.connect(self._save)
        root.addWidget(btn_save)

        # ── App Info ──────────────────────────────────────────
        info_grp = QGroupBox("Application Info")
        il = QVBoxLayout(info_grp)
        il.addWidget(QLabel(f"<b>App:</b> {APP_NAME}"))
        il.addWidget(QLabel(f"<b>Version:</b> {APP_VERSION}"))
        il.addWidget(QLabel(f"<b>Data:</b> C:\\JewelryBillingSystem\\data\\"))
        il.addWidget(QLabel(f"<b>Assets (Logo/QR):</b> {ASSETS_DIR}"))
        root.addWidget(info_grp)
        root.addStretch()

    # ── Image Helpers ─────────────────────────────────────────
    def _upload_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Shop Logo", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            _ensure_assets_dir()
            shutil.copy2(path, LOGO_FILE)
            self._load_logo_preview()
            QMessageBox.information(self, "Logo Uploaded", "Shop logo saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save logo:\n{e}")

    def _remove_logo(self):
        try:
            if os.path.exists(LOGO_FILE):
                os.remove(LOGO_FILE)
        except Exception:
            pass
        self.lbl_logo_preview.setPixmap(QPixmap())
        self.lbl_logo_preview.setText("No logo\nuploaded")

    def _upload_qr(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select QR Code Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            _ensure_assets_dir()
            shutil.copy2(path, QR_FILE)
            self._load_qr_preview()
            QMessageBox.information(self, "QR Uploaded", "QR code image saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save QR code:\n{e}")

    def _remove_qr(self):
        try:
            if os.path.exists(QR_FILE):
                os.remove(QR_FILE)
        except Exception:
            pass
        self.lbl_qr_preview.setPixmap(QPixmap())
        self.lbl_qr_preview.setText("No QR code\nuploaded")

    def _load_logo_preview(self):
        if os.path.exists(LOGO_FILE):
            pix = QPixmap(LOGO_FILE).scaled(
                96, 96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_logo_preview.setPixmap(pix)
            self.lbl_logo_preview.setText("")
        else:
            self.lbl_logo_preview.setPixmap(QPixmap())
            self.lbl_logo_preview.setText("No logo\nuploaded")

    def _load_qr_preview(self):
        if os.path.exists(QR_FILE):
            pix = QPixmap(QR_FILE).scaled(
                116, 116,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_qr_preview.setPixmap(pix)
            self.lbl_qr_preview.setText("")
        else:
            self.lbl_qr_preview.setPixmap(QPixmap())
            self.lbl_qr_preview.setText("No QR code\nuploaded")

    # ── Load & Save ───────────────────────────────────────────
    def refresh(self):
        AppConfig.load()
        shop = AppConfig.shop()
        self.txt_name.setText(shop.get("shop_name", ""))
        self.txt_tagline.setText(shop.get("tagline", ""))
        self.txt_owner.setText(shop.get("owner_name", ""))
        self.txt_addr.setText(shop.get("address", ""))
        self.txt_mobile.setText(shop.get("mobile", ""))
        self.txt_mobile2.setText(shop.get("mobile2", ""))
        self.txt_gst.setText(shop.get("gst_number", ""))
        self.txt_email.setText(shop.get("email", ""))
        self.txt_state.setText(shop.get("state", ""))
        self.txt_jurisdiction.setText(shop.get("jurisdiction", ""))
        self.txt_prefix.setText(shop.get("invoice_prefix", "JB"))
        self.txt_categories.setText(shop.get("categories", "Gold, Silver, Diamond, Platinum, Gemstone, Other"))
        self.txt_bank_name.setText(shop.get("bank_name", ""))
        self.txt_acc_name.setText(shop.get("account_name", ""))
        self.txt_acc_no.setText(shop.get("account_number", ""))
        self.txt_branch.setText(shop.get("bank_branch", ""))
        self.txt_ifsc.setText(shop.get("ifsc_code", ""))
        self.txt_terms.setPlainText(shop.get("terms", ""))
        self._load_logo_preview()
        self._load_qr_preview()

    def _save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Shop Name is required.")
            return
        data = {
            "shop_name":      self.txt_name.text().strip(),
            "tagline":        self.txt_tagline.text().strip(),
            "owner_name":     self.txt_owner.text().strip(),
            "address":        self.txt_addr.text().strip(),
            "mobile":         self.txt_mobile.text().strip(),
            "mobile2":        self.txt_mobile2.text().strip(),
            "gst_number":     self.txt_gst.text().strip(),
            "email":          self.txt_email.text().strip(),
            "state":          self.txt_state.text().strip(),
            "jurisdiction":   self.txt_jurisdiction.text().strip(),
            "invoice_prefix": self.txt_prefix.text().strip() or "JB",
            "categories":     self.txt_categories.text().strip(),
            "default_tax":    3.0,
            "bank_name":      self.txt_bank_name.text().strip(),
            "account_name":   self.txt_acc_name.text().strip(),
            "account_number": self.txt_acc_no.text().strip(),
            "bank_branch":    self.txt_branch.text().strip(),
            "ifsc_code":      self.txt_ifsc.text().strip(),
            "terms":          self.txt_terms.toPlainText().strip(),
        }
        if AppConfig.save_shop(data):
            AppConfig.load()
            QMessageBox.information(self, "Saved", "All settings saved successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")