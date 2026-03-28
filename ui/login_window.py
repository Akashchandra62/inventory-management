# ============================================================
# ui/login_window.py - Login Window
# ============================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from services.auth_service import authenticate
from app.constants import APP_NAME, COLOR_ACCENT


class LoginWindow(QWidget):
    """Login screen emits login_success signal on valid credentials."""

    login_success = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle(f"{APP_NAME} – Login")
        self.setMinimumSize(900, 580)

        # ── Root layout: left banner + right form ──────────────
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left banner
        banner = QFrame()
        banner.setStyleSheet("background-color: #2c3e50;")
        banner.setMinimumWidth(380)
        bl = QVBoxLayout(banner)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        gem = QLabel("💎")
        gem.setFont(QFont("Segoe UI", 52))
        gem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gem.setStyleSheet("color: #f39c12; background: transparent;")

        title = QLabel(APP_NAME)
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #f39c12; background: transparent;")

        sub = QLabel("Jewelry Shop Billing System")
        sub.setFont(QFont("Segoe UI", 11))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #ecf0f1; background: transparent;")

        bl.addWidget(gem)
        bl.addWidget(title)
        bl.addWidget(sub)

        # Right login form
        right = QFrame()
        right.setStyleSheet("background-color: #f5f6fa;")
        rl = QVBoxLayout(right)
        rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.setContentsMargins(60, 40, 60, 40)

        card = QFrame()
        card.setObjectName("login_card")
        card.setMinimumWidth(420)
        card.setMaximumWidth(500)
        card.setStyleSheet(
            "QFrame#login_card { background: white; border-radius: 12px;"
            " border: 1px solid #e0e0e0; padding: 30px; }"
        )
        cl = QVBoxLayout(card)
        cl.setSpacing(20)

        welcome = QLabel("Welcome Back")
        welcome.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        welcome.setStyleSheet("color: #2c3e50; background: transparent;")

        sign_in = QLabel("Sign in to continue")
        sign_in.setStyleSheet("color: #7f8c8d; font-size: 14px; background: transparent;")

        lbl_user = QLabel("Username")
        lbl_user.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px; background: transparent;")
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Enter username")
        self.txt_user.setMinimumHeight(48)
        self.txt_user.setStyleSheet(
            "QLineEdit { background: white; padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }"
            "QLineEdit:focus { border: 2px solid #f39c12; }"
        )

        lbl_pass = QLabel("Password")
        lbl_pass.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px; background: transparent;")
        self.txt_pass = QLineEdit()
        self.txt_pass.setPlaceholderText("Enter password")
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setMinimumHeight(48)
        self.txt_pass.setStyleSheet(
            "QLineEdit { background: white; padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }"
            "QLineEdit:focus { border: 2px solid #f39c12; }"
        )

        self.chk_show = QCheckBox("Show Password")
        self.chk_show.setStyleSheet("color: #555; font-size: 13px; background: transparent;")
        self.chk_show.toggled.connect(self._toggle_password)

        self.btn_login = QPushButton("Login")
        self.btn_login.setObjectName("btn_primary")
        self.btn_login.setMinimumHeight(48)
        self.btn_login.setStyleSheet(
            "QPushButton { background: #f39c12; color: white; border-radius: 6px;"
            " font-size: 16px; font-weight: bold; border: none; outline: none; }"
            "QPushButton:hover { background: #e67e22; }"
            "QPushButton:pressed { background: #d68910; }"
            "QPushButton:focus { outline: none; border: none; }"
        )
        self.btn_login.clicked.connect(self._do_login)
        self.txt_pass.returnPressed.connect(self._do_login)
        self.txt_user.returnPressed.connect(lambda: self.txt_pass.setFocus())

        cl.addWidget(welcome)
        cl.addWidget(sign_in)
        cl.addSpacing(10)
        cl.addWidget(lbl_user)
        cl.addWidget(self.txt_user)
        cl.addWidget(lbl_pass)
        cl.addWidget(self.txt_pass)
        cl.addWidget(self.chk_show)
        cl.addSpacing(6)
        cl.addWidget(self.btn_login)

        rl.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addWidget(banner)
        root.addWidget(right, 1)

    def _toggle_password(self, checked: bool):
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.txt_pass.setEchoMode(mode)

    def _do_login(self):
        user = self.txt_user.text().strip()
        pwd  = self.txt_pass.text()
        if not user or not pwd:
            QMessageBox.warning(self, "Login", "Please enter username and password.")
            return
        if authenticate(user, pwd):
            self.login_success.emit()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password.")
            self.txt_pass.clear()
            self.txt_pass.setFocus()

    def reset(self):
        self.txt_user.clear()
        self.txt_pass.clear()
        self.txt_user.setFocus()
