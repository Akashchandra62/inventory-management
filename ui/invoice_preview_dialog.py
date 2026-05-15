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

    Print path:  HTML → QTextDocument → QPrintDialog → printer
                 If no printer or user cancels → offer Save as PDF fallback.

    Preview rendering: QWebEngineView (if PyQtWebEngine installed) else QTextBrowser.
    Both paths work on Windows 7 / Windows 8 with PyQt5 ≥ 5.15.
    """

    def __init__(self, invoice: dict, parent=None):
        super().__init__(parent)
        self._invoice = invoice

        self.setWindowTitle("Invoice Preview")
        self.setMinimumSize(960, 740)
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowMinimizeButtonHint
        )
        self.setStyleSheet("QDialog{background:#f0f2f5;}")

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet("background:#2c3e50;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(16, 0, 16, 0)

        hdr_title = QLabel("Invoice Preview")
        hdr_title.setStyleSheet(
            "color:white;font-size:14px;font-weight:bold;background:transparent;"
        )
        inv_num = invoice.get("invoice_number", "")
        hdr_sub = QLabel(f"  {inv_num}" if inv_num else "")
        hdr_sub.setStyleSheet(
            "color:#f39c12;font-size:13px;font-weight:bold;background:transparent;"
        )
        hdr_l.addWidget(hdr_title)
        hdr_l.addWidget(hdr_sub)
        hdr_l.addStretch()
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
        btn_wrap.setFixedHeight(64)
        btn_wrap.setStyleSheet(
            "QWidget{background:#ecf0f1;border-top:2px solid #bdc3c7;}"
        )
        btn_hl = QHBoxLayout(btn_wrap)
        btn_hl.setContentsMargins(20, 12, 20, 12)
        btn_hl.setSpacing(12)

        def _mk_btn(label, bg, hover, min_w=160):
            b = QPushButton(label)
            b.setMinimumWidth(min_w)
            b.setFixedHeight(38)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{bg};color:white;border-radius:6px;"
                f"font-size:12px;font-weight:600;border:none;padding:0 14px;}}"
                f"QPushButton:hover{{background:{hover};}}"
                f"QPushButton:pressed{{opacity:0.85;}}"
            )
            return b

        # Left side: hint label
        hint = QLabel("Select copy type to print  →")
        hint.setStyleSheet(
            "color:#7f8c8d;font-size:11px;font-weight:600;background:transparent;"
        )

        btn_orig  = _mk_btn("🖨  Print Original",  "#27ae60", "#219a52")
        btn_dupl  = _mk_btn("🖨  Print Duplicate", "#2980b9", "#2471a3")
        btn_save  = _mk_btn("💾  Save PDF",        "#8e44ad", "#7d3c98", min_w=120)
        btn_close = _mk_btn("✖  Close",            "#95a5a6", "#7f8c8d", min_w=90)

        btn_orig.clicked.connect(lambda: self._do_print("Original Copy"))
        btn_dupl.clicked.connect(lambda: self._do_print("Duplicate Copy"))
        btn_save.clicked.connect(lambda: self._save_pdf("Original Copy"))
        btn_close.clicked.connect(self.reject)

        btn_hl.addWidget(hint)
        btn_hl.addStretch()
        btn_hl.addWidget(btn_orig)
        btn_hl.addWidget(btn_dupl)
        btn_hl.addWidget(btn_save)
        btn_hl.addWidget(btn_close)

        vl.addWidget(btn_wrap)

    # ── Actions ───────────────────────────────────────────────────

    def _do_print(self, copy_type: str):
        """Render invoice HTML into QTextDocument and send to system printer via QPrintDialog.
        Falls back to Save PDF if no printer is available or the dialog is cancelled.
        """
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
            dlg.setWindowTitle(f"Print  —  {copy_type}")

            if dlg.exec() == QPrintDialog.Accepted:
                doc.print_(printer)
            else:
                # User closed the print dialog (no printer selected or cancelled)
                self._offer_pdf_fallback(copy_type)

        except Exception:
            traceback.print_exc()
            self._offer_pdf_fallback(copy_type)

    def _offer_pdf_fallback(self, copy_type: str):
        """Ask user if they want to save as PDF when printing is not possible."""
        reply = QMessageBox.question(
            self,
            "No Printer Available",
            f"Could not print {copy_type}.\n\nSave as PDF instead?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self._save_pdf(copy_type)

    def _save_pdf(self, copy_type: str = "Original Copy"):
        """Open save-file dialog and generate a PDF for the current invoice."""
        try:
            from app.printer_helper import save_invoice_as_pdf
            save_invoice_as_pdf(self._invoice, parent=self, copy_type=copy_type)
        except Exception:
            traceback.print_exc()
            QMessageBox.critical(self, "Error", "Could not save PDF.")
