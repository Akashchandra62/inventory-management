# ============================================================
# utils.py - Shared utility functions
# ============================================================

import re
import uuid
from datetime import datetime


def current_datetime_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def current_date_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def format_currency(amount: float) -> str:
    """Format number as Indian Rupees string."""
    try:
        return f"₹ {float(amount):,.2f}"
    except (ValueError, TypeError):
        return "₹ 0.00"


def validate_mobile(mobile: str) -> bool:
    """Simple 10-digit Indian mobile validation."""
    return bool(re.match(r"^[6-9]\d{9}$", mobile.strip()))


def validate_gst(gst: str) -> bool:
    """Basic GST number format check (15 chars alphanumeric)."""
    return bool(re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gst.strip()))


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def unique_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def ask_due_payment_mode(parent, due_amount: float):
    """Show a dialog asking how the due was collected.
    Returns (db_field, label) e.g. ('cash_paid', 'Cash') or None if cancelled."""
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QButtonGroup, QRadioButton, QFrame,
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont

    dlg = QDialog(parent)
    dlg.setWindowTitle("How was the due collected?")
    dlg.setFixedWidth(340)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(20, 18, 20, 16)
    root.setSpacing(14)

    lbl = QLabel(f"Amount collected:  ₹ {due_amount:,.2f}")
    lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
    lbl.setStyleSheet("color:#2c3e50;")
    root.addWidget(lbl)

    sep = QFrame(); sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("color:#dde6ed;")
    root.addWidget(sep)

    grp = QButtonGroup(dlg)
    modes = [
        ("cash_paid",   "Cash",   "#27ae60"),
        ("upi_paid",    "UPI",    "#2980b9"),
        ("card_paid",   "Card",   "#8e44ad"),
        ("cheque_paid", "Cheque", "#f39c12"),
    ]
    _result = [None]

    btn_row = QHBoxLayout(); btn_row.setSpacing(8)
    for field, label, color in modes:
        rb = QRadioButton(label)
        rb.setStyleSheet(
            f"QRadioButton{{font-size:13px;font-weight:bold;color:{color};}}"
            f"QRadioButton::indicator{{width:16px;height:16px;}}"
        )
        grp.addButton(rb)
        btn_row.addWidget(rb)
        if field == "cash_paid":
            rb.setChecked(True)
            _result[0] = (field, label)
        rb._field = field
        rb._label = label
    root.addLayout(btn_row)

    def _on_toggled():
        for b in grp.buttons():
            if b.isChecked():
                _result[0] = (b._field, b._label)
    for b in grp.buttons():
        b.toggled.connect(_on_toggled)

    sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
    sep2.setStyleSheet("color:#dde6ed;")
    root.addWidget(sep2)

    act = QHBoxLayout(); act.addStretch()
    btn_ok = QPushButton("Confirm")
    btn_ok.setFixedHeight(34)
    btn_ok.setStyleSheet(
        "QPushButton{background:#27ae60;color:white;border-radius:5px;"
        "font-weight:bold;padding:0 20px;}"
        "QPushButton:hover{background:#219a52;}"
    )
    btn_cancel = QPushButton("Cancel")
    btn_cancel.setFixedHeight(34)
    btn_cancel.setStyleSheet(
        "QPushButton{background:#7f8c8d;color:white;border-radius:5px;padding:0 14px;}"
        "QPushButton:hover{background:#626567;}"
    )
    btn_ok.clicked.connect(dlg.accept)
    btn_cancel.clicked.connect(dlg.reject)
    act.addWidget(btn_cancel); act.addWidget(btn_ok)
    root.addLayout(act)

    if dlg.exec():
        return _result[0]
    return None
