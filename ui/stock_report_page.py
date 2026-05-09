# ============================================================
# ui/stock_report_page.py — Main Stock Ledger Report
# ============================================================

import csv
from datetime import date

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame,
    QHeaderView, QAbstractItemView, QScrollArea, QComboBox,
    QDateEdit, QFileDialog, QMessageBox, QGroupBox,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor

from services.stock_entry_service import get_all_entries


_FILTER_GRP = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#555;"
    "border:1px solid #dfe6e9;border-radius:6px;margin-top:8px;padding-top:4px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:10px;padding:0 4px;}"
)


class StockReportPage(QWidget):
    def __init__(self):
        super().__init__()
        self._entries: list[dict] = []
        self._current_data: list[dict] = []
        self._build_ui()

    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        root = QVBoxLayout(container)
        root.setContentsMargins(25, 20, 25, 20)
        root.setSpacing(12)

        # Title
        title = QLabel("📊  Stock Report")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        root.addWidget(title)

        # ── Filter group ───────────────────────────────────
        fgrp = QGroupBox("Filters")
        fgrp.setStyleSheet(_FILTER_GRP)
        fv = QVBoxLayout(fgrp)
        fv.setSpacing(6)
        fv.setContentsMargins(10, 8, 10, 10)

        # Row 1 — date range
        row1 = QHBoxLayout(); row1.setSpacing(8)

        row1.addWidget(self._lbl("From:"))
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd-MM-yyyy")
        today = QDate.currentDate()
        self.dt_from.setDate(QDate(today.year(), today.month(), 1))
        self.dt_from.setFixedHeight(30)
        row1.addWidget(self.dt_from)

        row1.addWidget(self._lbl("To:"))
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd-MM-yyyy")
        self.dt_to.setDate(today)
        self.dt_to.setFixedHeight(30)
        row1.addWidget(self.dt_to)

        btn_apply = QPushButton("Apply Date Range")
        btn_apply.setFixedHeight(30)
        btn_apply.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:4px;"
            "padding:2px 14px;font-size:11px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        btn_apply.clicked.connect(self._apply_with_dates)
        row1.addWidget(btn_apply)

        btn_from_start = QPushButton("From Start")
        btn_from_start.setFixedHeight(30)
        btn_from_start.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;border-radius:4px;"
            "padding:2px 12px;font-size:11px;border:none;}"
            "QPushButton:hover{background:#7d3c98;}"
        )
        btn_from_start.clicked.connect(self._apply_from_start)
        row1.addWidget(btn_from_start)

        btn_all = QPushButton("All Dates")
        btn_all.setFixedHeight(30)
        btn_all.setStyleSheet(
            "QPushButton{background:#7f8c8d;color:white;border-radius:4px;"
            "padding:2px 12px;font-size:11px;border:none;}"
            "QPushButton:hover{background:#626567;}"
        )
        btn_all.clicked.connect(self._apply_all_dates)
        row1.addWidget(btn_all)

        row1.addStretch()
        fv.addLayout(row1)

        # Row 2 — item filters
        row2 = QHBoxLayout(); row2.setSpacing(8)

        row2.addWidget(self._lbl("Metal:"))
        self.cmb_metal = QComboBox()
        self.cmb_metal.setFixedHeight(30)
        self.cmb_metal.setMinimumWidth(110)
        self.cmb_metal.currentTextChanged.connect(self._on_metal_changed)
        row2.addWidget(self.cmb_metal)

        row2.addWidget(self._lbl("Purity:"))
        self.cmb_purity = QComboBox()
        self.cmb_purity.setFixedHeight(30)
        self.cmb_purity.setMinimumWidth(86)
        self.cmb_purity.currentTextChanged.connect(self._refilter)
        row2.addWidget(self.cmb_purity)

        row2.addWidget(self._lbl("Item:"))
        self.txt_item = QLineEdit()
        self.txt_item.setPlaceholderText("Search item name…")
        self.txt_item.setFixedHeight(30)
        self.txt_item.setMinimumWidth(150)
        self.txt_item.textChanged.connect(self._refilter)
        row2.addWidget(self.txt_item)

        row2.addStretch()
        fv.addLayout(row2)
        root.addWidget(fgrp)

        # ── Table ──────────────────────────────────────────
        self.tbl = QTableWidget()
        _H = [
            "Product Details", "Purity",
            "O. A/c (g)", "Wt In (g)", "Wt Out (g)", "Closing (g)",
            "In Pcs", "Out Pcs", "Stock Pcs",
        ]
        self.tbl.setColumnCount(len(_H))
        self.tbl.setHorizontalHeaderLabels(_H)
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        _fixed = {1: 78, 2: 90, 3: 90, 4: 90, 5: 90, 6: 68, 7: 68, 8: 78}
        for c, w in _fixed.items():
            self.tbl.setColumnWidth(c, w)
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setMinimumHeight(400)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(30)
        root.addWidget(self.tbl)

        # ── Summary footer ─────────────────────────────────
        sf = QFrame()
        sf.setStyleSheet(
            "background:white; border:1px solid #e0e0e0;"
            "border-radius:5px; padding:6px;"
        )
        sl = QHBoxLayout(sf)
        self.lbl_rows    = QLabel("Items: 0")
        self.lbl_wt_in   = QLabel("Wt IN: 0.000 g")
        self.lbl_wt_out  = QLabel("Wt OUT: 0.000 g")
        self.lbl_closing = QLabel("Closing: 0.000 g")
        for lbl in (self.lbl_rows, self.lbl_wt_in, self.lbl_wt_out, self.lbl_closing):
            lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            lbl.setStyleSheet("background:transparent; color:#2c3e50;")
        sl.addWidget(self.lbl_rows)
        sl.addStretch()
        sl.addWidget(self.lbl_wt_in)
        sl.addStretch()
        sl.addWidget(self.lbl_wt_out)
        sl.addStretch()
        sl.addWidget(self.lbl_closing)
        root.addWidget(sf)

        # ── Export ─────────────────────────────────────────
        act = QHBoxLayout(); act.addStretch()
        btn_exp = QPushButton("📤  Export CSV")
        btn_exp.setStyleSheet(
            "QPushButton{background:#27ae60;color:white;border-radius:4px;"
            "padding:8px 16px;font-size:12px;border:none;}"
            "QPushButton:hover{background:#229954;}"
        )
        btn_exp.clicked.connect(self._export)
        act.addWidget(btn_exp)
        root.addLayout(act)

        # State: "all" | "range" | "from_start"
        self._date_mode = "all"

    # ──────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────
    @staticmethod
    def _lbl(text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:#444; font-size:11px; font-weight:600;")
        return l

    # ──────────────────────────────────────────────────────
    #  Public refresh — called when page is navigated to
    # ──────────────────────────────────────────────────────
    def refresh(self):
        self._entries = get_all_entries()
        self._rebuild_combos()
        # Keep whatever date/filter state was set; just re-run
        self._compute_and_display()

    # ──────────────────────────────────────────────────────
    #  Rebuild Metal / Purity combo options
    # ──────────────────────────────────────────────────────
    def _rebuild_combos(self):
        metals = sorted({e.get("metal_type", "") for e in self._entries if e.get("metal_type")})
        curr_metal = self.cmb_metal.currentText()
        self.cmb_metal.blockSignals(True)
        self.cmb_metal.clear()
        self.cmb_metal.addItem("All")
        self.cmb_metal.addItems(metals)
        idx = self.cmb_metal.findText(curr_metal)
        self.cmb_metal.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_metal.blockSignals(False)
        # Purity options depend on selected metal
        self._update_purity_combo(self.cmb_metal.currentText())

    def _update_purity_combo(self, metal_text: str):
        """Repopulate the Purity combo to only show purities for the selected metal."""
        if metal_text and metal_text != "All":
            purities = sorted({
                e.get("purity", "") for e in self._entries
                if e.get("metal_type", "") == metal_text and e.get("purity")
            })
        else:
            purities = sorted({e.get("purity", "") for e in self._entries if e.get("purity")})
        curr = self.cmb_purity.currentText()
        self.cmb_purity.blockSignals(True)
        self.cmb_purity.clear()
        self.cmb_purity.addItem("All")
        self.cmb_purity.addItems(purities)
        idx = self.cmb_purity.findText(curr)
        self.cmb_purity.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_purity.blockSignals(False)

    def _on_metal_changed(self, metal_text: str):
        """When metal filter changes, update purity options then refilter."""
        self._update_purity_combo(metal_text)
        self._refilter()

    # ──────────────────────────────────────────────────────
    #  Button actions
    # ──────────────────────────────────────────────────────
    def _apply_with_dates(self):
        self._date_mode = "range"
        self._compute_and_display()

    def _apply_from_start(self):
        self._date_mode = "from_start"
        self._compute_and_display()

    def _apply_all_dates(self):
        self._date_mode = "all"
        self._compute_and_display()

    def _refilter(self):
        """Called when a combo/textbox filter changes — reuse existing entries."""
        self._compute_and_display()

    # ──────────────────────────────────────────────────────
    #  Core computation
    # ──────────────────────────────────────────────────────
    @staticmethod
    def _is_invoice_out(e: dict) -> bool:
        """True when the OUT entry was auto-created by an invoice sale."""
        src = e.get("source", "")
        if src == "invoice":
            return True
        if src:
            return False
        # Legacy entries have no "source" field.
        # Only treat as invoice OUT if voucher_no looks like an invoice number
        # (starts with the shop prefix pattern, e.g. "JB-", "INV-").
        # Default to manual (False) for ambiguous cases to avoid overstating sales.
        vno = e.get("voucher_no", "").upper()
        return bool(vno) and not vno.startswith("VCH-") and "-" in vno and not vno.startswith("ADJ-")

    def _compute_and_display(self):
        if self._date_mode == "range":
            from_str = self.dt_from.date().toString("yyyy-MM-dd")
            to_str   = self.dt_to.date().toString("yyyy-MM-dd")
        elif self._date_mode == "from_start":
            from_str = ""
            to_str   = self.dt_to.date().toString("yyyy-MM-dd")
        else:  # "all"
            from_str = ""
            to_str   = ""

        metal  = self.cmb_metal.currentText()
        purity = self.cmb_purity.currentText()
        item_q = self.txt_item.text().strip().lower()

        # Bucket entries
        before: list[dict] = []   # before range → contributes to O. A/c
        period: list[dict] = []   # within range → contributes to Wt In / Wt Out

        for e in self._entries:
            if metal  != "All" and e.get("metal_type","") != metal:            continue
            if purity != "All" and e.get("purity","")     != purity:           continue
            if item_q and item_q not in e.get("item_name","").lower():          continue

            d = e.get("voucher_date","")
            if from_str and d < from_str:
                before.append(e)
            elif to_str and d > to_str:
                pass
            else:
                period.append(e)

        # Aggregate into groups keyed by (item_name, purity)
        groups: dict = {}

        def _get(e):
            key = (e.get("item_name",""), e.get("purity",""))
            if key not in groups:
                groups[key] = {
                    "item_name": key[0], "purity": key[1],
                    "open_wt":  0.0, "open_pcs": 0,
                    "wt_in":    0.0, "in_pcs":   0,
                    "wt_out":   0.0, "out_pcs":  0,
                    "adj_wt":   0.0, "adj_pcs":  0,
                }
            return groups[key]

        for e in before:
            g = _get(e)
            if e.get("entry_type") == "IN":
                g["open_wt"]  += e.get("net_wt",     0.0)
                g["open_pcs"] += e.get("qty_in",       0)
            else:
                # Both invoice and manual OUTs reduce the opening balance
                g["open_wt"]  -= e.get("out_net_wt",  0.0)
                g["open_pcs"] -= e.get("qty_out",       0)

        for e in period:
            g = _get(e)
            if e.get("entry_type") == "IN":
                g["wt_in"]  += e.get("net_wt",     0.0)
                g["in_pcs"] += e.get("qty_in",      0)
            elif self._is_invoice_out(e):
                # Invoice sale → visible in Wt Out / Out Pcs columns
                g["wt_out"]  += e.get("out_net_wt", 0.0)
                g["out_pcs"] += e.get("qty_out",    0)
            else:
                # Manual stock correction → silently reduces closing stock
                g["adj_wt"]  += e.get("out_net_wt", 0.0)
                g["adj_pcs"] += e.get("qty_out",    0)

        result = []
        for g in groups.values():
            g["closing_wt"] = round(
                g["open_wt"] + g["wt_in"] - g["wt_out"] - g["adj_wt"], 3
            )
            g["stock_pcs"]  = g["open_pcs"] + g["in_pcs"] - g["out_pcs"] - g["adj_pcs"]
            result.append(g)

        result.sort(key=lambda x: x.get("item_name","").lower())
        self._current_data = result
        self._populate(result)

    # ──────────────────────────────────────────────────────
    #  Populate table
    # ──────────────────────────────────────────────────────
    def _populate(self, data: list):
        self.tbl.setRowCount(0)
        t_open = t_in = t_out = t_close = 0.0
        t_in_pcs = t_out_pcs = t_stock = 0

        for g in data:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            closing = g["closing_wt"]
            stock   = g["stock_pcs"]

            vals = [
                g["item_name"],
                g["purity"],
                f"{g['open_wt']:.3f}",
                f"{g['wt_in']:.3f}",
                f"{g['wt_out']:.3f}",
                f"{closing:.3f}",
                str(g["in_pcs"]),
                str(g["out_pcs"]),
                str(stock),
            ]
            _right = {2, 3, 4, 5, 6, 7, 8}
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(
                    Qt.AlignRight | Qt.AlignVCenter if c in _right
                    else Qt.AlignLeft  | Qt.AlignVCenter
                )
                if c == 5:
                    cell.setForeground(
                        QColor("#1e8449") if closing > 0 else QColor("#e74c3c")
                    )
                if c == 8 and stock <= 0:
                    cell.setForeground(QColor("#e74c3c"))
                self.tbl.setItem(r, c, cell)

            t_open   += g["open_wt"]
            t_in     += g["wt_in"]
            t_out    += g["wt_out"]
            t_close  += closing
            t_in_pcs    += g["in_pcs"]
            t_out_pcs   += g["out_pcs"]
            t_stock     += stock

        # Totals footer row
        if data:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            fb = QColor("#eaf2ff")
            footer = [
                "TOTAL", "",
                f"{t_open:.3f}",
                f"{t_in:.3f}",
                f"{t_out:.3f}",
                f"{t_close:.3f}",
                str(t_in_pcs),
                str(t_out_pcs),
                str(t_stock),
            ]
            for c, v in enumerate(footer):
                cell = QTableWidgetItem(v)
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setBackground(fb)
                f = cell.font(); f.setBold(True); cell.setFont(f)
                self.tbl.setItem(r, c, cell)

        self.lbl_rows.setText(f"Items: {len(data)}")
        self.lbl_wt_in.setText(f"Wt IN: {t_in:.3f} g")
        self.lbl_wt_out.setText(f"Wt OUT: {t_out:.3f} g")
        self.lbl_closing.setText(f"Closing: {t_close:.3f} g")

    # ──────────────────────────────────────────────────────
    #  Export
    # ──────────────────────────────────────────────────────
    def _export(self):
        if not self._current_data:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV",
            f"stock_report_{date.today()}.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        fields = [
            "item_name", "purity",
            "open_wt", "wt_in", "wt_out", "closing_wt",
            "in_pcs", "out_pcs", "stock_pcs",
        ]
        headers = [
            "Product Details", "Purity",
            "O. A/c (g)", "Wt In (g)", "Wt Out (g)", "Closing (g)",
            "In Pcs", "Out Pcs", "Stock Pcs",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for g in self._current_data:
                writer.writerow([
                    g.get("item_name",""),
                    g.get("purity",""),
                    f"{g.get('open_wt',0.0):.3f}",
                    f"{g.get('wt_in',0.0):.3f}",
                    f"{g.get('wt_out',0.0):.3f}",
                    f"{g.get('closing_wt',0.0):.3f}",
                    g.get("in_pcs",0),
                    g.get("out_pcs",0),
                    g.get("stock_pcs",0),
                ])
        QMessageBox.information(self, "Export", f"Saved to:\n{path}")
