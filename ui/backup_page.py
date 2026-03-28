# ui/backup_page.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QGroupBox,
    QFrame, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from services.backup_service import backup_all, restore_backup
from app.constants import BACKUP_DIR
import os


class BackupPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(scroll)
        container = QWidget(); scroll.setWidget(container)
        root = QVBoxLayout(container); root.setContentsMargins(25,20,25,20); root.setSpacing(18)

        title = QLabel("💾  Backup & Restore"); title.setFont(QFont("Segoe UI",16,QFont.Weight.Bold))
        root.addWidget(title)

        # Backup section
        bgrp = QGroupBox("Backup Data")
        bl = QVBoxLayout(bgrp)
        bl.addWidget(QLabel("Create a backup copy of all your data (stock, invoices, customers, vendors)."))
        br = QHBoxLayout()
        self.txt_bdir = QLabel(f"Default: {BACKUP_DIR}")
        self.txt_bdir.setStyleSheet("color:#555; font-size:11px;")
        btn_choose = QPushButton("📁  Choose Folder")
        btn_choose.setStyleSheet("background:#7f8c8d;color:white;border-radius:4px;padding:7px 14px;")
        btn_choose.clicked.connect(self._choose_backup_dir)
        br.addWidget(self.txt_bdir); br.addStretch(); br.addWidget(btn_choose)
        bl.addLayout(br)
        btn_backup = QPushButton("💾  Create Backup Now")
        btn_backup.setStyleSheet("background:#27ae60;color:white;border-radius:5px;padding:10px 22px;font-weight:bold;")
        btn_backup.setMaximumWidth(220)
        btn_backup.clicked.connect(self._do_backup)
        bl.addWidget(btn_backup)
        root.addWidget(bgrp)

        # Restore section
        rgrp = QGroupBox("Restore Data")
        rl = QVBoxLayout(rgrp)
        rl.addWidget(QLabel("⚠️  Warning: Restoring will replace all current data with the backup copy."))
        btn_restore = QPushButton("📂  Select Backup & Restore")
        btn_restore.setStyleSheet("background:#e74c3c;color:white;border-radius:5px;padding:10px 22px;font-weight:bold;")
        btn_restore.setMaximumWidth(240)
        btn_restore.clicked.connect(self._do_restore)
        rl.addWidget(btn_restore)
        root.addWidget(rgrp)

        # Log
        log_grp = QGroupBox("Activity Log")
        ll = QVBoxLayout(log_grp)
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(150)
        self.log.setStyleSheet("font-size:11px; font-family: Consolas, monospace;")
        ll.addWidget(self.log)
        root.addWidget(log_grp)
        root.addStretch()

        self._backup_dir = BACKUP_DIR

    def _log(self, msg):
        self.log.append(msg)

    def _choose_backup_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder", self._backup_dir)
        if folder:
            self._backup_dir = folder
            self.txt_bdir.setText(f"Folder: {folder}")

    def _do_backup(self):
        ok, msg = backup_all(self._backup_dir)
        if ok:
            QMessageBox.information(self, "Backup", msg)
            self._log(f"✅ {msg}")
        else:
            QMessageBox.critical(self, "Backup Failed", msg)
            self._log(f"❌ {msg}")

    def _do_restore(self):
        reply = QMessageBox.warning(
            self, "Restore Confirmation",
            "This will REPLACE all current data with the backup.\n\nAre you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes: return

        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder to Restore", self._backup_dir)
        if not folder: return
        ok, msg = restore_backup(folder)
        if ok:
            QMessageBox.information(self, "Restore", msg)
            self._log(f"✅ {msg}")
        else:
            QMessageBox.critical(self, "Restore Failed", msg)
            self._log(f"❌ {msg}")

    def refresh(self):
        pass
