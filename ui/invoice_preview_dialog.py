from __future__ import annotations
import traceback

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextBrowser, QWidget, QLabel, QMessageBox,
)
from PyQt5.QtCore import Qt, QSizeF
from PyQt5.QtGui import QTextDocument

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView as _WebView
    _HAS_WEBENGINE = True
except ImportError:
    _HAS_WEBENGINE = False


class InvoicePreviewDialog(QDialog):
    """
    In-app invoice preview with Print Original / Print Duplicate / Save PDF options.
    Uses QWebEngineView when PyQtWebEngine is installed, else falls back to QTextBrowser.
    """

    def __init__(self, invoice: dict, parent=None):
        super().__init__(parent)
        self._invoice = invoice

        self.setWindowTitle("Invoice Preview")
        self.setMinimumSize(920, 700)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint
        )
        self.setStyleSheet("QDialog{background:#f5f6fa;}")

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────
        hdr = QLabel("   Invoice Preview")
        hdr.setFixedHeight(42)
        hdr.setStyleSheet(
            "background:#2c3e50;color:white;font-size:14px;font-weight:bold;"
            "padding-left:12px;"
        )
        vl.addWidget(hdr)

        # ── Preview area ──────────────────────────────────────────
        from app.printer_helper import build_html_preview
        html = build_html_preview(invoice)

        if _HAS_WEBENGINE:
            self._view = _WebView()
            self._view.setHtml(html)
        else:
            self._view = QTextBrowser()
            self._view.setOpenLinks(False)
            self._view.setHtml(html)
            self._view.setStyleSheet(
                "QTextBrowser{background:white;border:none;padding:8px;}"
            )

        vl.addWidget(self._view, 1)

        # ── Button bar ────────────────────────────────────────────
        btn_wrap = QWidget()
        btn_wrap.setFixedHeight(60)
        btn_wrap.setStyleSheet(
            "QWidget{background:#ecf0f1;border-top:1px solid #bdc3c7;}"
        )
        btn_hl = QHBoxLayout(btn_wrap)
        btn_hl.setContentsMargins(16, 11, 16, 11)
        btn_hl.setSpacing(10)

        def _mk_btn(label, bg, hover):
            b = QPushButton(label)
            b.setFixedHeight(36)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{bg};color:white;border-radius:6px;"
                f"font-size:12px;font-weight:600;border:none;padding:0 18px;}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
            return b

        btn_orig  = _mk_btn("Print Original",  "#27ae60", "#219a52")
        btn_dupl  = _mk_btn("Print Duplicate", "#2980b9", "#2471a3")
        btn_save  = _mk_btn("Save PDF",        "#8e44ad", "#7d3c98")
        btn_close = _mk_btn("Close",           "#e74c3c", "#c0392b")

        btn_orig.clicked.connect(lambda: self._do_print("Original Copy"))
        btn_dupl.clicked.connect(lambda: self._do_print("Duplicate Copy"))
        btn_save.clicked.connect(self._save_pdf)
        btn_close.clicked.connect(self.reject)

        btn_hl.addStretch()
        btn_hl.addWidget(btn_orig)
        btn_hl.addWidget(btn_dupl)
        btn_hl.addWidget(btn_save)
        btn_hl.addWidget(btn_close)

        vl.addWidget(btn_wrap)

    # ── Actions ───────────────────────────────────────────────────

    def _do_print(self, copy_type: str):
        """Send invoice directly to the system printer via QPrintDialog."""
        try:
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
            from app.printer_helper import build_html_preview

            html = build_html_preview(self._invoice, copy_type)
            doc  = QTextDocument()
            doc.setHtml(html)
            doc.setPageSize(QSizeF(595, 842))

            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)

            dlg = QPrintDialog(printer, self)
            dlg.setWindowTitle(f"Print {copy_type}")
            if dlg.exec() == QPrintDialog.Accepted:
                doc.print_(printer)

        except Exception:
            traceback.print_exc()
            QMessageBox.critical(
                self, "Print Error",
                "Could not open the print dialog.\n"
                "Please use Save PDF and print from there.",
            )

    def _save_pdf(self):
        """Open save-file dialog and generate a PDF for the current invoice."""
        try:
            from app.printer_helper import save_invoice_as_pdf
            save_invoice_as_pdf(self._invoice, parent=self)
        except Exception:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", "Could not save PDF.")
