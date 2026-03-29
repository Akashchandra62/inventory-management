# ============================================================
# ui/settings_page.py - Tabbed Settings (redesigned)
# ============================================================

import os
import shutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame, QScrollArea,
    QTextEdit, QFileDialog, QTabWidget, QSizePolicy, QApplication,
    QLayout, QSpacerItem, QGraphicsOpacityEffect,
    QComboBox, QCompleter
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QPoint, QSize, QRect, QMimeData, QByteArray, QTimer
)
from PyQt6.QtGui import (
    QFont, QPixmap, QPainter, QPen, QColor, QPainterPath,
    QIcon, QDrag
)
from app.config import AppConfig
from app.constants import APP_NAME, APP_VERSION, ASSETS_DIR, LOGO_FILE, QR_FILE
from services.auth_service import change_credentials, _get_credentials
from services.item_catalog_service import (
    get_catalog, add_catalog_item, update_catalog_item, delete_catalog_item
)

# ─── Chip colour palette ────────────────────────────────────
CHIP_COLORS = [
    "#5c6bc0", "#42a5f5", "#26c6da", "#26a69a", "#66bb6a",
    "#d4e157", "#ffca28", "#ffa726", "#ef5350", "#ec407a",
    "#ab47bc", "#7e57c2", "#29b6f6", "#26c6da", "#4db6ac",
    "#81c784", "#aed581", "#ff7043", "#8d6e63", "#78909c",
]


def _chip_color(text: str) -> str:
    return CHIP_COLORS[sum(ord(c) for c in text) % len(CHIP_COLORS)]


def _ensure_assets_dir():
    os.makedirs(ASSETS_DIR, exist_ok=True)


def _eye_icon(visible: bool) -> QIcon:
    size = 22
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#555555"), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(1, size / 2)
    path.quadTo(size / 2, 3, size - 1, size / 2)
    path.quadTo(size / 2, size - 3, 1, size / 2)
    p.drawPath(path)
    if visible:
        p.setBrush(QColor("#555555"))
        r = 3.5
        p.drawEllipse(int(size / 2 - r), int(size / 2 - r), int(r * 2), int(r * 2))
    else:
        pen2 = QPen(QColor("#555555"), 1.8)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        p.drawLine(4, size - 4, size - 4, 4)
    p.end()
    return QIcon(pix)


def _close_icon() -> QIcon:
    size = 16
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#ffffff"), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    margin = 4
    p.drawLine(margin, margin, size - margin, size - margin)
    p.drawLine(size - margin, margin, margin, size - margin)
    p.end()
    return QIcon(pix)


# ─── Flow Layout ────────────────────────────────────────────
class FlowLayout(QLayout):
    def __init__(self, parent=None, h_spacing=8, v_spacing=8):
        super().__init__(parent)
        self._items = []
        self._h = h_spacing
        self._v = v_spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(QRect(0, 0, width, 0), dry=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, dry=False)

    def sizeHint(self):
        return QSize(200, self._layout(QRect(0, 0, 200, 0), dry=True))

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _layout(self, rect, dry):
        m = self.contentsMargins()
        x, y = rect.x() + m.left(), rect.y() + m.top()
        right = rect.right() - m.right()
        line_h = 0
        for item in self._items:
            iw = item.sizeHint().width()
            ih = item.sizeHint().height()
            if x + iw > right and line_h > 0:
                x = rect.x() + m.left()
                y += line_h + self._v
                line_h = 0
            if not dry:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += iw + self._h
            line_h = max(line_h, ih)
        return y + line_h - rect.y() + m.bottom()


# ─── Category Chip ──────────────────────────────────────────
class CategoryChip(QFrame):
    delete_requested = pyqtSignal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.category_text = text
        self.color = _chip_color(text)
        self._drag_start = None
        self._build()

    def _build(self):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(32)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(10, 0, 8, 0)
        hl.setSpacing(5)

        grip = QLabel("⠿")
        grip.setStyleSheet("color: rgba(255,255,255,160); font-size:12px; background:transparent;")
        grip.setFixedWidth(12)

        lbl = QLabel(self.category_text)
        lbl.setStyleSheet("color:white; font-weight:600; font-size:12px; background:transparent;")

        btn_del = QPushButton()
        btn_del.setIcon(_close_icon())
        btn_del.setIconSize(QSize(10, 10))
        btn_del.setFixedSize(18, 18)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(
            "QPushButton{background:rgba(0,0,0,0.22);color:white;"
            "border-radius:9px;border:none;}"
            "QPushButton:hover{background:rgba(0,0,0,0.45);}"
        )
        btn_del.clicked.connect(self._on_delete)

        hl.addWidget(grip)
        hl.addWidget(lbl)
        hl.addWidget(btn_del)

        # Width from content
        fm = lbl.fontMetrics()
        w = fm.horizontalAdvance(self.category_text) + 12 + 18 + 10 + 8 + 10
        self.setFixedWidth(max(w, 70))

        r, g, b = int(self.color[1:3], 16), int(self.color[3:5], 16), int(self.color[5:7], 16)
        dark = f"#{max(0,r-25):02x}{max(0,g-25):02x}{max(0,b-25):02x}"
        self.setStyleSheet(f"""
            CategoryChip {{
                background: {self.color};
                border-radius: 16px;
            }}
            CategoryChip:hover {{
                background: {dark};
            }}
        """)

    def _on_delete(self):
        # Fade out then emit
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self.delete_requested.emit(self.category_text))
        anim.start()
        self._anim = anim  # keep reference

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton and
                self._drag_start is not None):
            delta = (event.position().toPoint() - self._drag_start).manhattanLength()
            if delta >= QApplication.startDragDistance():
                self._start_drag()
        super().mouseMoveEvent(event)

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.category_text)
        drag.setMimeData(mime)

        # Build a slightly transparent pixmap so the cursor image looks lifted
        src = self.grab()
        dragged_pix = QPixmap(src.size())
        dragged_pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(dragged_pix)
        p.setOpacity(0.85)
        p.drawPixmap(0, 0, src)
        p.end()
        drag.setPixmap(dragged_pix)
        drag.setHotSpot(QPoint(dragged_pix.width() // 2, dragged_pix.height() // 2))

        # Ghost the original chip so it looks like it has been picked up
        ghost = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(ghost)
        ghost.setOpacity(0.25)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

        drag.exec(Qt.DropAction.MoveAction)

        # Restore after drop
        self.setGraphicsEffect(None)
        self.setCursor(Qt.CursorShape.OpenHandCursor)


# ─── Categories Editor ──────────────────────────────────────
class CategoriesEditor(QWidget):
    changed = pyqtSignal()   # emitted whenever order / content changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories: list[str] = []
        self.setAcceptDrops(True)
        self._drop_idx = -1   # visual indicator position

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Chips area
        self._chips_widget = QWidget()
        self._chips_widget.setAcceptDrops(True)
        self._chips_widget.installEventFilter(self)
        self._flow = FlowLayout(self._chips_widget, h_spacing=8, v_spacing=8)
        self._chips_widget.setLayout(self._flow)
        root.addWidget(self._chips_widget)

        # Add row
        add_row = QHBoxLayout()
        self._txt_add = QLineEdit()
        self._txt_add.setPlaceholderText("Type category name and press Add...")
        self._txt_add.setFixedHeight(34)
        self._txt_add.setStyleSheet(
            "QLineEdit{border:1px solid #ced4da;border-radius:6px;padding:0 10px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid #3498db;}"
        )
        self._txt_add.returnPressed.connect(self._add_category)

        btn_add = QPushButton("+ Add")
        btn_add.setFixedSize(72, 34)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(
            "QPushButton{background:#3498db;color:white;border-radius:6px;"
            "font-size:13px;font-weight:600;border:none;}"
            "QPushButton:hover{background:#2980b9;}"
        )
        btn_add.clicked.connect(self._add_category)

        add_row.addWidget(self._txt_add)
        add_row.addWidget(btn_add)
        root.addLayout(add_row)

    # ── Public API ───────────────────────────────────────────
    def set_categories(self, cats: list[str]):
        self._categories = list(cats)
        self._rebuild_chips()

    def get_categories(self) -> list[str]:
        return list(self._categories)

    # ── Internal ─────────────────────────────────────────────
    def _rebuild_chips(self):
        # Remove all chips from flow layout
        while self._flow.count():
            item = self._flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for cat in self._categories:
            self._add_chip_widget(cat, animate=False)

        self._chips_widget.updateGeometry()
        self._chips_widget.update()

    def _add_chip_widget(self, text: str, animate=True):
        chip = CategoryChip(text, self._chips_widget)
        chip.delete_requested.connect(self._remove_category)
        self._flow.addWidget(chip)

        if animate:
            eff = QGraphicsOpacityEffect(chip)
            chip.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", chip)
            anim.setDuration(300)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            chip._fade_in = anim

        self._chips_widget.updateGeometry()
        self.updateGeometry()

    def _add_category(self):
        text = self._txt_add.text().strip()
        if not text:
            return
        if text in self._categories:
            QMessageBox.warning(self.window(), "Duplicate", f'"{text}" already exists.')
            return
        self._categories.append(text)
        self._add_chip_widget(text, animate=True)
        self._txt_add.clear()
        self.changed.emit()

    def _remove_category(self, text: str):
        if text in self._categories:
            self._categories.remove(text)
        # Remove chip widget
        for i in range(self._flow.count()):
            item = self._flow.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), CategoryChip):
                if item.widget().category_text == text:
                    w = self._flow.takeAt(i).widget()
                    QTimer.singleShot(220, w.deleteLater)
                    break
        self._chips_widget.updateGeometry()
        self.updateGeometry()
        self.changed.emit()

    # ── Drag & Drop ──────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        dragged_text = event.mimeData().text()
        if dragged_text not in self._categories:
            event.ignore()
            return

        # Find drop position from cursor
        pos = self._chips_widget.mapFrom(self, event.position().toPoint())
        target_idx = self._find_drop_index(pos)

        old_idx = self._categories.index(dragged_text)
        if old_idx == target_idx or old_idx == target_idx - 1:
            event.ignore()
            return

        self._categories.pop(old_idx)
        insert_at = target_idx if target_idx <= old_idx else target_idx - 1
        self._categories.insert(insert_at, dragged_text)
        self._rebuild_chips()
        event.acceptProposedAction()
        self.changed.emit()

    def eventFilter(self, obj, event):
        if obj is self._chips_widget:
            from PyQt6.QtCore import QEvent
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasText():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.DragMove:
                if event.mimeData().hasText():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                # Forward to parent dropEvent
                dragged_text = event.mimeData().text()
                if dragged_text not in self._categories:
                    return False
                pos = event.position().toPoint()
                target_idx = self._find_drop_index(pos)
                old_idx = self._categories.index(dragged_text)
                if old_idx != target_idx and old_idx != target_idx - 1:
                    self._categories.pop(old_idx)
                    insert_at = target_idx if target_idx <= old_idx else target_idx - 1
                    self._categories.insert(insert_at, dragged_text)
                    self._rebuild_chips()
                    self.changed.emit()
                event.acceptProposedAction()
                return True
        return super().eventFilter(obj, event)

    def _find_drop_index(self, pos: QPoint) -> int:
        """Return index to insert before based on cursor position."""
        best_idx = len(self._categories)
        best_dist = float("inf")
        for i in range(self._flow.count()):
            item = self._flow.itemAt(i)
            if not item or not item.widget():
                continue
            geom = item.widget().geometry()
            center_x = geom.center().x()
            center_y = geom.center().y()
            dist = abs(pos.x() - center_x) + abs(pos.y() - center_y)
            if dist < best_dist:
                best_dist = dist
                # Insert before or after based on x position
                best_idx = i if pos.x() < center_x else i + 1
        return best_idx


# ─── Password field with eye toggle ─────────────────────────
def _pw_row(placeholder: str):
    row = QWidget()
    row.setStyleSheet("background:transparent;")
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)

    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setFixedHeight(36)
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    field.setStyleSheet(
        "QLineEdit{background:white;border:1px solid #ced4da;border-radius:6px;padding:0 10px;font-size:13px;}"
        "QLineEdit:focus{border:1px solid #8e44ad;}"
    )

    btn = QPushButton()
    btn.setIcon(_eye_icon(False))
    btn.setFixedSize(36, 36)
    btn.setCheckable(True)
    btn.setToolTip("Show / Hide password")
    btn.setStyleSheet(
        "QPushButton{background:white;border:1px solid #ced4da;border-radius:6px;}"
        "QPushButton:checked{border-color:#8e44ad;background:#f5eefb;}"
        "QPushButton:hover{background:#f0eaf7;}"
    )
    btn.toggled.connect(lambda checked, f=field, b=btn: (
        f.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password),
        b.setIcon(_eye_icon(checked))
    ))

    hl.addWidget(field)
    hl.addWidget(btn)
    return row, field


# ─── Helper: create a scrollable tab page ───────────────────
def _scroll_tab():
    outer = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setWidget(outer)
    root = QVBoxLayout(outer)
    root.setContentsMargins(24, 20, 24, 24)
    root.setSpacing(18)
    wrap = QWidget()
    wrap_l = QVBoxLayout(wrap)
    wrap_l.setContentsMargins(0, 0, 0, 0)
    wrap_l.addWidget(scroll)
    wrap_l.setSpacing(0)
    return wrap, root   # wrap goes into tab; root is where you addWidget


def _le(ph=""):
    e = QLineEdit()
    e.setPlaceholderText(ph)
    e.setMinimumHeight(34)
    return e


def _grp(title):
    g = QGroupBox(title)
    f = g, None
    return g


def _section(title):
    g = QGroupBox(title)
    g.setStyleSheet(
        "QGroupBox{font-weight:bold;font-size:13px;border:1px solid #dfe6e9;"
        "border-radius:8px;margin-top:18px;padding-top:10px;}"
        "QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 6px;color:#2c3e50;}"
    )
    return g


def _save_btn(label="💾  Save Changes"):
    b = QPushButton(label)
    b.setFixedHeight(40)
    b.setMaximumWidth(220)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton{background:#f39c12;color:white;border-radius:7px;"
        "font-size:13px;font-weight:bold;border:none;}"
        "QPushButton:hover{background:#e67e22;}"
    )
    return b


# ════════════════════════════════════════════════════════════
#  Main Settings Page
# ════════════════════════════════════════════════════════════
class SettingsPage(QWidget):

    def __init__(self):
        super().__init__()
        self._categories: list[str] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Page title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(52)
        title_bar.setStyleSheet("background:#2c3e50;")
        tb_l = QHBoxLayout(title_bar)
        tb_l.setContentsMargins(24, 0, 24, 0)
        lbl_title = QLabel("⚙️  Settings")
        lbl_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color:white;")
        tb_l.addWidget(lbl_title)
        tb_l.addStretch()
        root.addWidget(title_bar)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #f5f6fa;
            }
            QTabBar::tab {
                background: #dfe6e9;
                color: #636e72;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: 600;
                border: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #f39c12;
                color: white;
                border-radius: 0px;
            }
            QTabBar::tab:hover:!selected {
                background: #b2bec3;
                color: #2c3e50;
            }
        """)

        self._tabs.addTab(self._build_profile_tab(),  "👤  Profile")
        self._tabs.addTab(self._build_payment_tab(),  "💳  Payment & QR")
        self._tabs.addTab(self._build_general_tab(),  "🛠  General")
        self._tabs.addTab(self._build_items_tab(),    "📦  Items")

        root.addWidget(self._tabs)

    # ════════════════════════════════════════════════════════
    #  TAB 4 — Item Catalog (predefined item name master list)
    # ════════════════════════════════════════════════════════
    def _build_items_tab(self):
        self._catalog: list[dict] = []
        wrap, root = _scroll_tab()

        sec = _section("📋  Item Catalog")
        sec_l = QVBoxLayout(sec)
        sec_l.setContentsMargins(16, 18, 16, 16)
        sec_l.setSpacing(10)

        hint = QLabel(
            "Pre-define item names here. When adding stock you can pick from this list "
            "(with prefix search) or type a new name — it will be added automatically."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#7f8c8d;font-size:11px;")
        sec_l.addWidget(hint)

        # ── Add new item row (top) ───────────────────────────
        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        self._new_item_name = QLineEdit()
        self._new_item_name.setPlaceholderText("New item name  (e.g. Gold Necklace)")
        self._new_item_name.setFixedHeight(36)
        self._new_item_name.setStyleSheet(
            "QLineEdit{border:1px solid #ced4da;border-radius:6px;padding:0 10px;"
            "font-size:13px;background:white;}"
            "QLineEdit:focus{border:1px solid #3949ab;}"
        )
        self._new_item_name.returnPressed.connect(self._add_catalog_item)

        self._new_item_cat = QComboBox()
        self._new_item_cat.setFixedHeight(36)
        self._new_item_cat.setMinimumWidth(140)
        self._new_item_cat.setStyleSheet(
            "QComboBox{border:1px solid #ced4da;border-radius:6px;"
            "padding:0 8px;font-size:13px;background:white;}"
            "QComboBox::drop-down{border:none;}"
        )

        btn_add_cat = QPushButton("+ Add")
        btn_add_cat.setFixedHeight(36)
        btn_add_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_cat.setStyleSheet(
            "QPushButton{background:#3949ab;color:white;border-radius:6px;"
            "font-size:13px;font-weight:600;border:none;padding:0 18px;}"
            "QPushButton:hover{background:#283593;}"
        )
        btn_add_cat.clicked.connect(self._add_catalog_item)

        add_row.addWidget(self._new_item_name, 1)
        add_row.addWidget(self._new_item_cat)
        add_row.addWidget(btn_add_cat)
        sec_l.addLayout(add_row)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color:#e8ecef;")
        sec_l.addWidget(div)

        # Search + count row
        search_row = QHBoxLayout()
        self._cat_search = QLineEdit()
        self._cat_search.setPlaceholderText("🔍  Search catalog…")
        self._cat_search.setFixedHeight(32)
        self._cat_search.setStyleSheet(
            "QLineEdit{border:1px solid #ced4da;border-radius:6px;padding:0 10px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid #8e44ad;}"
        )
        self._cat_search.textChanged.connect(self._filter_catalog)
        self._catalog_count = QLabel("0 items")
        self._catalog_count.setStyleSheet("color:#7f8c8d;font-size:11px;min-width:60px;")
        self._catalog_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        search_row.addWidget(self._cat_search, 1)
        search_row.addWidget(self._catalog_count)
        sec_l.addLayout(search_row)

        # Card list — items rendered directly here (tab already scrolls)
        self._catalog_list_widget = QWidget()
        self._catalog_list_widget.setStyleSheet("background:transparent;")
        self._catalog_list_layout = QVBoxLayout(self._catalog_list_widget)
        self._catalog_list_layout.setContentsMargins(0, 0, 0, 0)
        self._catalog_list_layout.setSpacing(6)
        sec_l.addWidget(self._catalog_list_widget)

        root.addWidget(sec)
        root.addStretch()
        return wrap

    def _rebuild_catalog_categories(self):
        cats = AppConfig.categories()
        self._new_item_cat.clear()
        self._new_item_cat.addItem("(no category)")
        self._new_item_cat.addItems(cats)

    def _refresh_catalog(self):
        self._catalog = get_catalog()
        self._rebuild_catalog_categories()
        self._filter_catalog()

    def _filter_catalog(self):
        query = self._cat_search.text().strip().lower()
        visible = [
            i for i in self._catalog
            if not query or query in i.get("name", "").lower()
        ]

        # Clear existing rows
        while self._catalog_list_layout.count():
            item = self._catalog_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not visible:
            placeholder = QLabel("No items yet — add one using the form below.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(
                "color:#b2bec3;font-size:13px;padding:28px;background:transparent;"
            )
            self._catalog_list_layout.addWidget(placeholder)
        else:
            for entry in visible:
                self._catalog_list_layout.addWidget(self._make_catalog_row(entry))

        self._catalog_list_layout.addStretch()
        self._catalog_count.setText(
            f"{len(visible)} item{'s' if len(visible) != 1 else ''}" +
            (f" (of {len(self._catalog)})" if len(visible) != len(self._catalog) else "")
        )

    def _make_catalog_row(self, entry: dict) -> QWidget:
        name = entry.get("name", "")
        cat  = entry.get("category", "")

        card = QFrame()
        card.setFixedHeight(52)
        card.setStyleSheet(
            "QFrame{background:white;border:1px solid #e8ecef;"
            "border-radius:8px;}"
            "QFrame:hover{border-color:#c5cae9;background:#fdfdff;}"
        )
        hl = QHBoxLayout(card)
        hl.setContentsMargins(14, 0, 10, 0)
        hl.setSpacing(10)

        # Colored left accent bar
        accent = QFrame()
        accent.setFixedSize(4, 28)
        color = _chip_color(name)
        accent.setStyleSheet(f"background:{color};border-radius:2px;border:none;")

        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(
            "font-size:13px;font-weight:600;color:#2c3e50;background:transparent;border:none;"
        )

        lbl_cat = QLabel(cat) if cat else None
        if lbl_cat:
            cat_color = _chip_color(cat)
            lbl_cat.setStyleSheet(
                f"background:{cat_color};color:white;font-size:10px;font-weight:600;"
                f"border-radius:10px;padding:3px 12px;border:none;"
            )
            lbl_cat.setFixedHeight(22)

        btn_edit = QPushButton("✎  Edit")
        btn_edit.setFixedHeight(30)
        btn_edit.setMinimumWidth(68)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(
            "QPushButton{background:#eef2ff;color:#3949ab;border-radius:6px;"
            "font-size:11px;font-weight:600;border:1px solid #c5cae9;padding:0 10px;}"
            "QPushButton:hover{background:#c5cae9;color:#1a237e;}"
        )
        btn_edit.clicked.connect(lambda _, n=name: self._edit_catalog_item(n))

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(30, 30)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(
            "QPushButton{background:#fdecea;color:#c0392b;border-radius:6px;"
            "font-size:12px;font-weight:700;border:1px solid #f5c6cb;}"
            "QPushButton:hover{background:#e74c3c;color:white;border-color:#e74c3c;}"
        )
        btn_del.clicked.connect(lambda _, n=name: self._delete_catalog_item(n))

        hl.addWidget(accent)
        hl.addWidget(lbl_name, 1)
        if lbl_cat:
            hl.addWidget(lbl_cat)
        hl.addWidget(btn_edit)
        hl.addWidget(btn_del)
        return card

    def _add_catalog_item(self):
        name = self._new_item_name.text().strip()
        if not name:
            return
        cat = self._new_item_cat.currentText()
        if cat == "(no category)":
            cat = ""
        ok = add_catalog_item(name, cat)
        if not ok:
            QMessageBox.warning(self, "Duplicate", f'"{name}" already exists in the catalog.')
            return
        self._new_item_name.clear()
        self._cat_search.clear()
        self._refresh_catalog()

    def _edit_catalog_item(self, old_name: str):
        # Inline: show a small dialog to rename
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Item")
        dlg.setMinimumWidth(320)
        dlg.setStyleSheet("QDialog{background:#f5f6fa;}")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(10)

        entry = next((i for i in self._catalog if i["name"] == old_name), {})

        lbl = QLabel("Item Name *")
        lbl.setStyleSheet("font-weight:600;font-size:11px;color:#555;")
        txt = QLineEdit(old_name)
        txt.setFixedHeight(34)
        txt.setStyleSheet(
            "QLineEdit{border:1px solid #ced4da;border-radius:6px;"
            "padding:0 10px;font-size:13px;background:white;}"
            "QLineEdit:focus{border-color:#8e44ad;}"
        )
        lbl2 = QLabel("Category")
        lbl2.setStyleSheet("font-weight:600;font-size:11px;color:#555;")
        cmb = QComboBox()
        cmb.setFixedHeight(34)
        cmb.addItem("(no category)")
        cmb.addItems(AppConfig.categories())
        if entry.get("category"):
            idx = cmb.findText(entry["category"])
            if idx >= 0:
                cmb.setCurrentIndex(idx)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)

        vl.addWidget(lbl); vl.addWidget(txt)
        vl.addWidget(lbl2); vl.addWidget(cmb)
        vl.addWidget(bb)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_name = txt.text().strip()
        new_cat  = cmb.currentText()
        if new_cat == "(no category)":
            new_cat = ""
        if not new_name:
            return
        update_catalog_item(old_name, new_name, new_cat)
        self._refresh_catalog()

    def _delete_catalog_item(self, name: str):
        reply = QMessageBox.question(
            self, "Remove Item",
            f'Remove "{name}" from the catalog?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_catalog_item(name)
            self._refresh_catalog()

    # ════════════════════════════════════════════════════════
    #  TAB 1 — Profile
    # ════════════════════════════════════════════════════════
    def _build_profile_tab(self):
        wrap, root = _scroll_tab()

        # ── Credentials ──────────────────────────────────────
        sec = _section("🔒  Login Credentials")
        sec_l = QVBoxLayout(sec)
        sec_l.setContentsMargins(16, 12, 16, 16)
        sec_l.setSpacing(10)

        card = QWidget()
        card.setMaximumWidth(420)
        card.setStyleSheet("background:#f8f9fa;border-radius:8px;")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(16, 14, 16, 14)
        card_l.setSpacing(10)

        def cred_field(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color:#444;font-size:12px;font-weight:600;background:transparent;")
            card_l.addWidget(lbl)
            card_l.addWidget(widget)

        self.txt_new_username = QLineEdit()
        self.txt_new_username.setFixedHeight(36)
        self.txt_new_username.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.txt_new_username.setStyleSheet(
            "QLineEdit{background:white;border:1px solid #ced4da;border-radius:6px;padding:0 10px;font-size:13px;}"
            "QLineEdit:focus{border:1px solid #8e44ad;}"
        )

        row_cur,  self.txt_current_pass = _pw_row("Current password")
        row_new,  self.txt_new_pass     = _pw_row("New password")
        row_conf, self.txt_confirm_pass = _pw_row("Confirm new password")

        cred_field("Username",         self.txt_new_username)
        cred_field("Current Password", row_cur)
        cred_field("New Password",     row_new)
        cred_field("Confirm Password", row_conf)

        btn_cred = QPushButton("Update Credentials")
        btn_cred.setFixedHeight(36)
        btn_cred.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_cred.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cred.setStyleSheet(
            "QPushButton{background:#8e44ad;color:white;border-radius:6px;"
            "font-size:13px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#7d3c98;}"
        )
        btn_cred.clicked.connect(self._change_credentials)
        card_l.addSpacing(4)
        card_l.addWidget(btn_cred)

        sec_l.addWidget(card)
        root.addWidget(sec)

        # ── Shop Logo ─────────────────────────────────────────
        logo_sec = _section("🖼  Shop Logo")
        logo_l = QHBoxLayout(logo_sec)
        logo_l.setContentsMargins(16, 12, 16, 16)
        logo_l.setSpacing(20)

        self.lbl_logo_preview = QLabel("No logo\nuploaded")
        self.lbl_logo_preview.setFixedSize(100, 100)
        self.lbl_logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo_preview.setStyleSheet(
            "border:2px dashed #bdc3c7;border-radius:8px;color:#7f8c8d;font-size:11px;"
        )

        logo_btns = QVBoxLayout()
        btn_ul = QPushButton("📁  Upload Logo")
        btn_ul.setStyleSheet(
            "QPushButton{background:#2980b9;color:white;border-radius:5px;padding:8px 16px;border:none;}"
            "QPushButton:hover{background:#2471a3;}"
        )
        btn_ul.clicked.connect(self._upload_logo)
        btn_rm = QPushButton("🗑  Remove")
        btn_rm.setStyleSheet(
            "QPushButton{background:#e74c3c;color:white;border-radius:5px;padding:8px 16px;border:none;}"
            "QPushButton:hover{background:#c0392b;}"
        )
        btn_rm.clicked.connect(self._remove_logo)
        logo_note = QLabel("Accepted: PNG, JPG\nRecommended: square")
        logo_note.setStyleSheet("color:#7f8c8d;font-size:11px;")
        logo_btns.addWidget(btn_ul)
        logo_btns.addWidget(btn_rm)
        logo_btns.addWidget(logo_note)
        logo_btns.addStretch()

        logo_l.addWidget(self.lbl_logo_preview)
        logo_l.addLayout(logo_btns)
        logo_l.addStretch()
        root.addWidget(logo_sec)

        # ── Shop Info ─────────────────────────────────────────
        info_sec = _section("🏪  Shop Information")
        info_l = QVBoxLayout(info_sec)
        info_l.setContentsMargins(16, 12, 16, 16)
        info_l.setSpacing(8)

        def row(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(130)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("color:#555;font-size:12px;")
            r.addWidget(lbl)
            r.addWidget(widget)
            info_l.addLayout(r)

        self.txt_name         = _le("Shop name *")
        self.txt_tagline      = _le("e.g. Deals In All Type Of Hallmark Jewellery")
        self.txt_owner        = _le("Owner / Proprietor name")
        self.txt_addr         = _le("Full shop address")
        self.txt_mobile       = _le("Primary mobile number")
        self.txt_mobile2      = _le("Second mobile (optional)")
        self.txt_gst          = _le("GST number")
        self.txt_email        = _le("Email (optional)")

        row("Shop Name *",   self.txt_name)
        row("Tagline",       self.txt_tagline)
        row("Owner Name",    self.txt_owner)
        row("Address *",     self.txt_addr)
        row("Mobile *",      self.txt_mobile)
        row("Mobile 2",      self.txt_mobile2)
        row("GST Number",    self.txt_gst)
        row("Email",         self.txt_email)

        root.addWidget(info_sec)

        btn = _save_btn("💾  Save Profile")
        btn.clicked.connect(self._save)
        root.addWidget(btn)
        root.addStretch()
        return wrap

    # ════════════════════════════════════════════════════════
    #  TAB 2 — Payment & QR
    # ════════════════════════════════════════════════════════
    def _build_payment_tab(self):
        wrap, root = _scroll_tab()

        # Bank Details
        bank_sec = _section("🏦  Bank Details")
        bank_l = QVBoxLayout(bank_sec)
        bank_l.setContentsMargins(16, 12, 16, 16)
        bank_l.setSpacing(8)

        def brow(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(130)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("color:#555;font-size:12px;")
            r.addWidget(lbl)
            r.addWidget(widget)
            bank_l.addLayout(r)

        self.txt_bank_name = _le("e.g. HDFC BANK")
        self.txt_acc_name  = _le("Account holder name")
        self.txt_acc_no    = _le("Account number")
        self.txt_branch    = _le("Branch name and location")
        self.txt_ifsc      = _le("IFSC code e.g. HDFC0002052")

        brow("Bank Name",    self.txt_bank_name)
        brow("Account Name", self.txt_acc_name)
        brow("Account No.",  self.txt_acc_no)
        brow("Branch",       self.txt_branch)
        brow("IFSC Code",    self.txt_ifsc)
        root.addWidget(bank_sec)

        # QR Code
        qr_sec = _section("📱  Payment QR Code")
        qr_l = QHBoxLayout(qr_sec)
        qr_l.setContentsMargins(16, 12, 16, 16)
        qr_l.setSpacing(20)

        self.lbl_qr_preview = QLabel("No QR code\nuploaded")
        self.lbl_qr_preview.setFixedSize(120, 120)
        self.lbl_qr_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr_preview.setStyleSheet(
            "border:2px dashed #bdc3c7;border-radius:8px;color:#7f8c8d;font-size:11px;"
        )

        qr_btns = QVBoxLayout()
        btn_uqr = QPushButton("📁  Upload QR Code")
        btn_uqr.setStyleSheet(
            "QPushButton{background:#27ae60;color:white;border-radius:5px;padding:8px 16px;border:none;}"
            "QPushButton:hover{background:#229954;}"
        )
        btn_uqr.clicked.connect(self._upload_qr)
        btn_rqr = QPushButton("🗑  Remove")
        btn_rqr.setStyleSheet(
            "QPushButton{background:#e74c3c;color:white;border-radius:5px;padding:8px 16px;border:none;}"
            "QPushButton:hover{background:#c0392b;}"
        )
        btn_rqr.clicked.connect(self._remove_qr)
        qr_note = QLabel(
            "Download from PhonePe / GPay /\nPaytm and upload here.\n"
            "Shown on every invoice."
        )
        qr_note.setStyleSheet("color:#7f8c8d;font-size:11px;")
        qr_btns.addWidget(btn_uqr)
        qr_btns.addWidget(btn_rqr)
        qr_btns.addWidget(qr_note)
        qr_btns.addStretch()

        qr_l.addWidget(self.lbl_qr_preview)
        qr_l.addLayout(qr_btns)
        qr_l.addStretch()
        root.addWidget(qr_sec)

        # Terms
        terms_sec = _section("📋  Terms & Conditions")
        terms_l = QVBoxLayout(terms_sec)
        terms_l.setContentsMargins(16, 12, 16, 16)
        self.txt_terms = QTextEdit()
        self.txt_terms.setPlaceholderText(
            "Enter each condition on a new line.\n"
            "1. सन देन के समय रसीद लेना आवश्यक है।\n"
            "2. ऑर्डर देने के समय 70% जमा देना अनिवार्य है।"
        )
        self.txt_terms.setMinimumHeight(130)
        terms_l.addWidget(self.txt_terms)
        root.addWidget(terms_sec)

        btn = _save_btn("💾  Save Payment Info")
        btn.clicked.connect(self._save)
        root.addWidget(btn)
        root.addStretch()
        return wrap

    # ════════════════════════════════════════════════════════
    #  TAB 3 — General Settings
    # ════════════════════════════════════════════════════════
    def _build_general_tab(self):
        wrap, root = _scroll_tab()

        # Invoice settings
        inv_sec = _section("🧾  Invoice Settings")
        inv_l = QVBoxLayout(inv_sec)
        inv_l.setContentsMargins(16, 12, 16, 16)
        inv_l.setSpacing(8)

        def irow(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(150)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setStyleSheet("color:#555;font-size:12px;")
            r.addWidget(lbl)
            r.addWidget(widget)
            r.addStretch()
            inv_l.addLayout(r)

        self.txt_prefix       = _le("Invoice prefix e.g. JB")
        self.txt_prefix.setMaximumWidth(160)
        self.txt_state        = _le("e.g. Bihar Code : 10")
        self.txt_jurisdiction = _le("e.g. ROHTAS")

        irow("Invoice Prefix",  self.txt_prefix)
        irow("State",           self.txt_state)
        irow("Jurisdiction",    self.txt_jurisdiction)
        root.addWidget(inv_sec)

        # Categories
        cat_sec = _section("🏷  Item Categories")
        cat_sec_l = QVBoxLayout(cat_sec)
        cat_sec_l.setContentsMargins(16, 12, 16, 16)
        cat_sec_l.setSpacing(8)

        hint = QLabel("Drag chips to reorder  •  Order here = order in all dropdowns")
        hint.setStyleSheet("color:#7f8c8d;font-size:11px;")
        cat_sec_l.addWidget(hint)

        self._cat_editor = CategoriesEditor()
        cat_sec_l.addWidget(self._cat_editor)
        root.addWidget(cat_sec)

        # App info
        info_sec = _section("ℹ️  Application Info")
        info_l = QVBoxLayout(info_sec)
        info_l.setContentsMargins(16, 12, 16, 16)
        for line in [
            f"<b>App:</b> {APP_NAME}",
            f"<b>Version:</b> {APP_VERSION}",
            f"<b>Data:</b> C:\\JewelryBillingSystem\\data\\",
            f"<b>Assets:</b> {ASSETS_DIR}",
        ]:
            lbl = QLabel(line)
            lbl.setStyleSheet("font-size:12px;")
            info_l.addWidget(lbl)
        root.addWidget(info_sec)

        btn = _save_btn("💾  Save Settings")
        btn.clicked.connect(self._save)
        root.addWidget(btn)
        root.addStretch()
        return wrap

    # ════════════════════════════════════════════════════════
    #  Logic
    # ════════════════════════════════════════════════════════
    def _change_credentials(self):
        new_user   = self.txt_new_username.text().strip()
        current_pw = self.txt_current_pass.text()
        new_pw     = self.txt_new_pass.text()
        confirm_pw = self.txt_confirm_pass.text()
        if not new_user:
            QMessageBox.warning(self, "Validation", "Username cannot be empty."); return
        if not current_pw:
            QMessageBox.warning(self, "Validation", "Enter your current password."); return
        if not new_pw:
            QMessageBox.warning(self, "Validation", "New password cannot be empty."); return
        if new_pw != confirm_pw:
            QMessageBox.warning(self, "Validation", "Passwords do not match."); return
        ok, msg = change_credentials(current_pw, new_user, new_pw)
        if ok:
            QMessageBox.information(self, "Success", msg)
            self.txt_current_pass.clear()
            self.txt_new_pass.clear()
            self.txt_confirm_pass.clear()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _upload_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg)")
        if not path: return
        try:
            _ensure_assets_dir()
            shutil.copy2(path, LOGO_FILE)
            self._load_logo_preview()
            QMessageBox.information(self, "Uploaded", "Logo saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _remove_logo(self):
        try:
            if os.path.exists(LOGO_FILE): os.remove(LOGO_FILE)
        except Exception: pass
        self.lbl_logo_preview.setPixmap(QPixmap())
        self.lbl_logo_preview.setText("No logo\nuploaded")

    def _upload_qr(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select QR Code", "", "Images (*.png *.jpg *.jpeg)")
        if not path: return
        try:
            _ensure_assets_dir()
            shutil.copy2(path, QR_FILE)
            self._load_qr_preview()
            QMessageBox.information(self, "Uploaded", "QR Code saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _remove_qr(self):
        try:
            if os.path.exists(QR_FILE): os.remove(QR_FILE)
        except Exception: pass
        self.lbl_qr_preview.setPixmap(QPixmap())
        self.lbl_qr_preview.setText("No QR code\nuploaded")

    def _load_logo_preview(self):
        if os.path.exists(LOGO_FILE):
            pix = QPixmap(LOGO_FILE).scaled(
                96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.lbl_logo_preview.setPixmap(pix)
            self.lbl_logo_preview.setText("")
        else:
            self.lbl_logo_preview.setPixmap(QPixmap())
            self.lbl_logo_preview.setText("No logo\nuploaded")

    def _load_qr_preview(self):
        if os.path.exists(QR_FILE):
            pix = QPixmap(QR_FILE).scaled(
                116, 116, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.lbl_qr_preview.setPixmap(pix)
            self.lbl_qr_preview.setText("")
        else:
            self.lbl_qr_preview.setPixmap(QPixmap())
            self.lbl_qr_preview.setText("No QR code\nuploaded")

    def refresh(self):
        user, _ = _get_credentials()
        self.txt_new_username.setText(user)

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
        self.txt_bank_name.setText(shop.get("bank_name", ""))
        self.txt_acc_name.setText(shop.get("account_name", ""))
        self.txt_acc_no.setText(shop.get("account_number", ""))
        self.txt_branch.setText(shop.get("bank_branch", ""))
        self.txt_ifsc.setText(shop.get("ifsc_code", ""))
        self.txt_terms.setPlainText(shop.get("terms", ""))

        cats_str = shop.get("categories", "Gold, Silver, Diamond, Platinum, Gemstone, Other")
        cats = [c.strip() for c in cats_str.split(",") if c.strip()]
        self._cat_editor.set_categories(cats)

        self._load_logo_preview()
        self._load_qr_preview()
        self._refresh_catalog()

    def _save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Validation", "Shop Name is required.")
            return
        cats = self._cat_editor.get_categories()
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
            "categories":     ", ".join(cats),
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
            QMessageBox.information(self, "Saved", "Settings saved successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
