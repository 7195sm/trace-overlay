"""
Trace Overlay — Transparent image overlay for tracing practice.

A lightweight always-on-top tool that displays a semi-transparent image
over your screen. Enable click-through mode to draw in the app underneath
(MS Paint, Clip Studio, Photoshop, etc.) while seeing the reference above.

Usage:
    pip install PyQt5
    python trace_overlay.py

Platform: Windows 10/11 (click-through uses Win32 API)
"""

import sys
import os
import ctypes
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSlider, QSpinBox, QCheckBox,
    QVBoxLayout, QHBoxLayout, QFrame, QFileDialog, QMessageBox, QShortcut,
)
from PyQt5.QtCore import Qt, QPoint, QRect, QUrl
from PyQt5.QtGui import (
    QPainter, QPixmap, QColor, QPen, QKeySequence, QTransform, QDragEnterEvent,
    QDropEvent,
)

# ── Win32 constants ───────────────────────────────────────────
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

EDGE_MARGIN = 8       # px — resize handle detection zone
OPACITY_STEP = 5      # % per keyboard shortcut press
ROTATION_STEP = 2     # degrees per keyboard shortcut press
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}

VERSION = "1.4.0"

# ── Settings persistence ─────────────────────────────────────
SETTINGS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "TraceOverlay"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "panel_x": 100,
    "panel_y": 100,
    "overlay_x": 200,
    "overlay_y": 100,
    "overlay_w": 800,
    "overlay_h": 600,
    "opacity": 50,
    "last_image": "",
    "rotation": 0,
    "flip_h": False,
    "flip_v": False,
    "lock_aspect": True,
}


def load_settings() -> dict:
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULT_SETTINGS, **saved}
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(data: dict):
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class OverlayWindow(QWidget):
    """Frameless, always-on-top transparent overlay that displays an image."""

    def __init__(self):
        super().__init__()
        self.image: QPixmap | None = None
        self._display_image: QPixmap | None = None  # transformed cache
        self.opacity_value: float = 0.5
        self._rotation: float = 0.0       # 0.0 – 359.9
        self._flip_h: bool = False
        self._flip_v: bool = False
        self._click_through: bool = False
        self._dragging: bool = False
        self._resizing: bool = False
        self._drag_start: QPoint = QPoint()
        self._resize_edge: str = ""
        self._start_geometry: QRect = QRect()
        self.lock_aspect: bool = True
        self.aspect_ratio: float = 800 / 600

        self.setWindowTitle("Trace Overlay")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # hide from taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(100, 100)
        self.resize(800, 600)

    # ── Click-through ────────────────────────────────────────
    def set_click_through(self, enabled: bool):
        """Toggle WS_EX_TRANSPARENT so mouse events pass to windows below."""
        if sys.platform != "win32":
            return
        self._click_through = enabled
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enabled:
            style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
            style |= WS_EX_LAYERED
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    # ── Image / Opacity ──────────────────────────────────────
    def set_image(self, pixmap: QPixmap):
        self.image = pixmap
        self._rebuild_display()

    def set_opacity(self, value: float):
        self.opacity_value = max(0.05, min(1.0, value))
        self.update()

    # ── Rotation & Flip ──────────────────────────────────────
    def set_rotation(self, degrees: float):
        self._rotation = degrees % 360
        self._rebuild_display()

    def rotate_by(self, delta: float):
        self.set_rotation(self._rotation + delta)

    def flip_horizontal(self):
        self._flip_h = not self._flip_h
        self._rebuild_display()

    def flip_vertical(self):
        self._flip_v = not self._flip_v
        self._rebuild_display()

    def set_transform(self, rotation: float, flip_h: bool, flip_v: bool):
        """Restore transform state (e.g. from saved settings)."""
        self._rotation = rotation % 360
        self._flip_h = flip_h
        self._flip_v = flip_v
        if self.image:
            self._rebuild_display()

    @property
    def rotation(self) -> float:
        return self._rotation

    @property
    def flip_h(self) -> bool:
        return self._flip_h

    @property
    def flip_v(self) -> bool:
        return self._flip_v

    def _rebuild_display(self):
        """Apply rotation + flip to the source image and cache the result."""
        if not self.image:
            self._display_image = None
            self.update()
            return
        xform = QTransform()
        if self._rotation:
            xform = xform.rotate(self._rotation)
        if self._flip_h:
            xform = xform.scale(-1, 1)
        if self._flip_v:
            xform = xform.scale(1, -1)
        self._display_image = self.image.transformed(xform, Qt.SmoothTransformation)
        self.update()

    # ── Painting ─────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if not self._click_through:
            painter.fillRect(self.rect(), QColor(40, 40, 40, 25))
            painter.setPen(QPen(QColor(0, 120, 255, 120), 2, Qt.DashLine))
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        else:
            painter.setPen(QPen(QColor(100, 100, 100, 40), 1))
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        img = self._display_image
        if img:
            painter.setOpacity(self.opacity_value)
            scaled = img.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

        painter.end()

    # ── Mouse: drag to move & edge-resize ────────────────────
    def _edge_at(self, pos: QPoint) -> str:
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        edges = ""
        if y < EDGE_MARGIN:
            edges += "t"
        elif y > h - EDGE_MARGIN:
            edges += "b"
        if x < EDGE_MARGIN:
            edges += "l"
        elif x > w - EDGE_MARGIN:
            edges += "r"
        return edges

    def _update_cursor(self, edges: str):
        cursor_map = {
            "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
            "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
            "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
            "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor,
        }
        self.setCursor(cursor_map.get(edges, Qt.ArrowCursor))

    def mousePressEvent(self, event):
        if self._click_through or event.button() != Qt.LeftButton:
            return
        edges = self._edge_at(event.pos())
        if edges:
            self._resizing = True
            self._resize_edge = edges
            self._drag_start = event.globalPos()
            self._start_geometry = self.geometry()
        else:
            self._dragging = True
            self._drag_start = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self._click_through:
            return
        if self._dragging:
            self.move(event.globalPos() - self._drag_start)
        elif self._resizing:
            self._do_resize(event.globalPos())
        else:
            self._update_cursor(self._edge_at(event.pos()))

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self._resize_edge = ""

    def _do_resize(self, global_pos: QPoint):
        dx = global_pos.x() - self._drag_start.x()
        dy = global_pos.y() - self._drag_start.y()
        g = QRect(self._start_geometry)
        min_w, min_h = self.minimumWidth(), self.minimumHeight()

        if "r" in self._resize_edge:
            g.setWidth(max(min_w, g.width() + dx))
        if "b" in self._resize_edge:
            g.setHeight(max(min_h, g.height() + dy))
        if "l" in self._resize_edge:
            new_left = g.left() + dx
            if g.right() - new_left >= min_w:
                g.setLeft(new_left)
        if "t" in self._resize_edge:
            new_top = g.top() + dy
            if g.bottom() - new_top >= min_h:
                g.setTop(new_top)

        # Apply aspect ratio constraint
        if self.lock_aspect and self.aspect_ratio > 0:
            edge = self._resize_edge
            has_h = ("l" in edge or "r" in edge)
            has_v = ("t" in edge or "b" in edge)
            if has_h and not has_v:
                # Width changed — adjust height
                g.setHeight(max(min_h, int(g.width() / self.aspect_ratio)))
            elif has_v and not has_h:
                # Height changed — adjust width
                g.setWidth(max(min_w, int(g.height() * self.aspect_ratio)))
            elif has_h and has_v:
                # Corner drag — width leads
                g.setHeight(max(min_h, int(g.width() / self.aspect_ratio)))

        self.setGeometry(g)


class ControlPanel(QWidget):
    """Control panel — the main window that manages the overlay."""

    STYLE = """
        QWidget {
            font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
            font-size: 13px;
        }
        QPushButton {
            padding: 7px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: #f5f5f5;
        }
        QPushButton:hover { background: #e8e8e8; }
        QPushButton:pressed { background: #ddd; }
        QPushButton:checked {
            background: #d0e8ff;
            border-color: #4a9eff;
            color: #0060c0;
        }
        QSlider::groove:horizontal {
            height: 6px;
            background: #ddd;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            width: 16px; height: 16px;
            margin: -5px 0;
            background: #4a9eff;
            border-radius: 8px;
        }
        QSpinBox {
            padding: 4px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
    """

    def __init__(self):
        super().__init__()
        self.overlay = OverlayWindow()
        self._current_image_path: str = ""
        self._aspect_ratio: float = 800 / 600  # w / h
        self._updating_spin: bool = False       # guard against recursive spin updates
        self._settings = load_settings()
        self._build_ui()
        self._setup_shortcuts()
        self._restore_settings()

    # ── Drag-and-drop ────────────────────────────────────────
    def _enable_drag_drop(self):
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    ext = Path(url.toLocalFile()).suffix.lower()
                    if ext in IMAGE_EXTENSIONS:
                        event.acceptProposedAction()
                        return

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                ext = Path(path).suffix.lower()
                if ext in IMAGE_EXTENSIONS:
                    self._load_image(path)
                    return

    def _build_ui(self):
        self.setWindowTitle("Trace Overlay")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedWidth(330)
        self.setStyleSheet(self.STYLE)
        self._enable_drag_drop()

        root = QVBoxLayout()
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        # ── Title ──
        title = QLabel("Trace Overlay")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        root.addWidget(title)
        subtitle = QLabel("Transparent image overlay for tracing practice")
        subtitle.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 4px;")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        root.addWidget(self._sep())

        # ── Open Image ──
        self.open_btn = QPushButton("Open Image  (Ctrl+O)")
        self.open_btn.setStyleSheet(
            self.open_btn.styleSheet()
            + "font-size: 14px; padding: 10px;"
        )
        self.open_btn.clicked.connect(self._open_image)
        root.addWidget(self.open_btn)

        self.file_label = QLabel("No image loaded  (or drag && drop here)")
        self.file_label.setStyleSheet("color: gray; font-size: 11px;")
        self.file_label.setWordWrap(True)
        root.addWidget(self.file_label)

        root.addWidget(self._sep())

        # ── Opacity ──
        root.addWidget(QLabel("Opacity  (Ctrl+[ / Ctrl+])"))
        row = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(5, 100)
        self.opacity_slider.setValue(50)
        self.opacity_slider.valueChanged.connect(self._on_opacity)
        row.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("50%")
        self.opacity_label.setFixedWidth(38)
        self.opacity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.opacity_label)
        root.addLayout(row)

        root.addWidget(self._sep())

        # ── Click-through toggle ──
        self.lock_btn = QPushButton("Enable Click-Through  (Ctrl+T)")
        self.lock_btn.setCheckable(True)
        self.lock_btn.toggled.connect(self._toggle_click_through)
        root.addWidget(self.lock_btn)

        info = QLabel(
            "ON: clicks pass through to the app below\n"
            "OFF: drag to move / resize the overlay"
        )
        info.setStyleSheet("color: #999; font-size: 10px;")
        root.addWidget(info)

        root.addWidget(self._sep())

        # ── Rotation slider ──
        root.addWidget(QLabel("Rotation  (Ctrl+R / Ctrl+Shift+R, 2\u00b0 step)"))
        rot_row = QHBoxLayout()
        self.rot_slider = QSlider(Qt.Horizontal)
        self.rot_slider.setRange(0, 359)
        self.rot_slider.setValue(0)
        self.rot_slider.valueChanged.connect(self._on_rotation_slider)
        rot_row.addWidget(self.rot_slider)
        self.rot_label = QLabel("0\u00b0")
        self.rot_label.setFixedWidth(38)
        self.rot_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        rot_row.addWidget(self.rot_label)
        root.addLayout(rot_row)

        # Quick rotate + flip buttons
        xform_row = QHBoxLayout()
        xform_row.setSpacing(4)

        self.rot_ccw_btn = QPushButton("\u21b6 -90\u00b0")
        self.rot_ccw_btn.setToolTip("Rotate counter-clockwise 90\u00b0")
        self.rot_ccw_btn.clicked.connect(lambda: self._rotate_by(-90))
        xform_row.addWidget(self.rot_ccw_btn)

        self.rot_cw_btn = QPushButton("+90\u00b0 \u21b7")
        self.rot_cw_btn.setToolTip("Rotate clockwise 90\u00b0")
        self.rot_cw_btn.clicked.connect(lambda: self._rotate_by(90))
        xform_row.addWidget(self.rot_cw_btn)

        self.rot_reset_btn = QPushButton("0\u00b0")
        self.rot_reset_btn.setToolTip("Reset rotation")
        self.rot_reset_btn.clicked.connect(self._reset_rotation)
        self.rot_reset_btn.setFixedWidth(36)
        xform_row.addWidget(self.rot_reset_btn)

        self.flip_h_btn = QPushButton("\u2194 Flip H")
        self.flip_h_btn.setToolTip("Flip horizontal (Ctrl+Shift+H)")
        self.flip_h_btn.setCheckable(True)
        self.flip_h_btn.clicked.connect(self._flip_h)
        xform_row.addWidget(self.flip_h_btn)

        self.flip_v_btn = QPushButton("\u2195 Flip V")
        self.flip_v_btn.setToolTip("Flip vertical (Ctrl+Shift+V)")
        self.flip_v_btn.setCheckable(True)
        self.flip_v_btn.clicked.connect(self._flip_v)
        xform_row.addWidget(self.flip_v_btn)

        root.addLayout(xform_row)

        root.addWidget(self._sep())

        # ── Size controls ──
        root.addWidget(QLabel("Overlay Size"))

        self.lock_aspect_cb = QCheckBox("Lock aspect ratio  (Ctrl+L)")
        self.lock_aspect_cb.setChecked(True)
        self.lock_aspect_cb.setStyleSheet("font-size: 11px;")
        self.lock_aspect_cb.toggled.connect(self._on_lock_aspect_toggled)
        root.addWidget(self.lock_aspect_cb)

        size_row = QHBoxLayout()
        self.w_spin = QSpinBox()
        self.w_spin.setRange(100, 4000)
        self.w_spin.setValue(800)
        self.w_spin.setSuffix(" px")
        self.w_spin.valueChanged.connect(self._on_w_changed)
        size_row.addWidget(self.w_spin)
        size_row.addWidget(QLabel("\u00d7"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(100, 4000)
        self.h_spin.setValue(600)
        self.h_spin.setSuffix(" px")
        self.h_spin.valueChanged.connect(self._on_h_changed)
        size_row.addWidget(self.h_spin)
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(50)
        apply_btn.clicked.connect(self._apply_size)
        size_row.addWidget(apply_btn)
        root.addLayout(size_row)

        self.fit_btn = QPushButton("Fit to Original Image Size  (Ctrl+F)")
        self.fit_btn.clicked.connect(self._fit_to_image)
        self.fit_btn.setEnabled(False)
        root.addWidget(self.fit_btn)

        root.addWidget(self._sep())

        # ── Shortcut reference ──
        shortcuts_text = (
            "Ctrl+O          Open image\n"
            "Ctrl+T          Toggle click-through\n"
            "Ctrl+H          Hide / show overlay\n"
            "Ctrl+[ / ]      Opacity down / up\n"
            "Ctrl+R          Rotate CW 2\u00b0\n"
            "Ctrl+Shift+R    Rotate CCW 2\u00b0\n"
            "Ctrl+Shift+H    Flip horizontal\n"
            "Ctrl+Shift+V    Flip vertical\n"
            "Ctrl+L          Lock aspect ratio\n"
            "Ctrl+F          Fit to image size"
        )
        sc_label = QLabel(shortcuts_text)
        sc_label.setStyleSheet(
            "color: #888; font-size: 10px; font-family: 'Consolas', 'Courier New', monospace;"
        )
        root.addWidget(sc_label)

        root.addStretch()

        # ── Footer ──
        footer = QLabel(f"v{VERSION}  \u00b7  Closing this panel closes the overlay")
        footer.setStyleSheet("color: #aaa; font-size: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

        self.setLayout(root)

    def _setup_shortcuts(self):
        """Register keyboard shortcuts on BOTH the control panel and the overlay."""
        bindings = {
            "Ctrl+O": self._open_image,
            "Ctrl+T": lambda: self.lock_btn.toggle(),
            "Ctrl+H": self._toggle_overlay_visible,
            "Ctrl+[": self._opacity_down,
            "Ctrl+]": self._opacity_up,
            "Ctrl+F": self._fit_to_image,
            "Ctrl+R": lambda: self._rotate_by(ROTATION_STEP),
            "Ctrl+Shift+R": lambda: self._rotate_by(-ROTATION_STEP),
            "Ctrl+Shift+H": self._flip_h,
            "Ctrl+Shift+V": self._flip_v,
            "Ctrl+L": self._toggle_lock_aspect,
        }
        for key, slot in bindings.items():
            # Register on control panel
            QShortcut(QKeySequence(key), self).activated.connect(slot)
            # Register on overlay window too
            QShortcut(QKeySequence(key), self.overlay).activated.connect(slot)

    # ── Settings persistence ─────────────────────────────────
    def _restore_settings(self):
        s = self._settings
        self.move(s["panel_x"], s["panel_y"])
        self.overlay.move(s["overlay_x"], s["overlay_y"])
        self.overlay.resize(s["overlay_w"], s["overlay_h"])
        self._updating_spin = True
        self.w_spin.setValue(s["overlay_w"])
        self.h_spin.setValue(s["overlay_h"])
        self._updating_spin = False
        self.opacity_slider.setValue(s["opacity"])
        self.lock_aspect_cb.setChecked(s.get("lock_aspect", True))
        self._aspect_ratio = s["overlay_w"] / max(1, s["overlay_h"])
        self._sync_aspect_to_overlay()

        # Restore last image if it still exists
        last = s.get("last_image", "")
        if last and os.path.isfile(last):
            self._load_image(last)
            # Restore transform after image is loaded
            rot = s.get("rotation", 0)
            fh = s.get("flip_h", False)
            fv = s.get("flip_v", False)
            self.overlay.set_transform(rot, fh, fv)
            self.rot_slider.setValue(int(rot) % 360)
            self.flip_h_btn.setChecked(fh)
            self.flip_v_btn.setChecked(fv)
            self._update_rot_label()

    def _save_settings(self):
        pos = self.pos()
        opos = self.overlay.pos()
        data = {
            "panel_x": pos.x(),
            "panel_y": pos.y(),
            "overlay_x": opos.x(),
            "overlay_y": opos.y(),
            "overlay_w": self.overlay.width(),
            "overlay_h": self.overlay.height(),
            "opacity": self.opacity_slider.value(),
            "last_image": self._current_image_path,
            "rotation": self.overlay.rotation,
            "flip_h": self.overlay.flip_h,
            "flip_v": self.overlay.flip_v,
            "lock_aspect": self.lock_aspect_cb.isChecked(),
        }
        save_settings(data)

    @staticmethod
    def _sep() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        return line

    # ── Image loading (shared by open, drop, and restore) ────
    def _load_image(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Error", "Could not load this image.")
            return

        self._current_image_path = path
        self.overlay.set_image(pixmap)

        # Constrain to screen size
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(pixmap.width(), screen.width() - 50)
        h = min(pixmap.height(), screen.height() - 50)
        self.overlay.resize(w, h)
        self._updating_spin = True
        self.w_spin.setValue(w)
        self.h_spin.setValue(h)
        self._updating_spin = False

        self.overlay.show()
        self.fit_btn.setEnabled(True)

        # Set aspect ratio from image
        self._aspect_ratio = pixmap.width() / max(1, pixmap.height())
        self._sync_aspect_to_overlay()

        # Reset transform for new image
        self.overlay.set_transform(0, False, False)
        self.rot_slider.setValue(0)
        self.flip_h_btn.setChecked(False)
        self.flip_v_btn.setChecked(False)
        self._update_rot_label()

        name = os.path.basename(path)
        self.file_label.setText(f"{name}  ({pixmap.width()} \u00d7 {pixmap.height()} px)")

    # ── Slots ─────────────────────────────────────────────────
    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;All Files (*)",
        )
        if path:
            self._load_image(path)

    def _on_opacity(self, value: int):
        self.opacity_label.setText(f"{value}%")
        self.overlay.set_opacity(value / 100.0)

    def _opacity_down(self):
        self.opacity_slider.setValue(max(5, self.opacity_slider.value() - OPACITY_STEP))

    def _opacity_up(self):
        self.opacity_slider.setValue(min(100, self.opacity_slider.value() + OPACITY_STEP))

    def _toggle_click_through(self, checked: bool):
        self.overlay.set_click_through(checked)
        if checked:
            self.lock_btn.setText("Disable Click-Through  (Ctrl+T)")
        else:
            self.lock_btn.setText("Enable Click-Through  (Ctrl+T)")

    def _toggle_overlay_visible(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()

    # ── Rotation ─────────────────────────────────────────────
    def _on_rotation_slider(self, value: int):
        self.overlay.set_rotation(float(value))
        self._update_rot_label()

    def _rotate_by(self, delta: float):
        new_rot = (self.overlay.rotation + delta) % 360
        self.rot_slider.setValue(int(new_rot))
        # set_rotation is called via slider's valueChanged signal

    def _reset_rotation(self):
        self.rot_slider.setValue(0)

    def _flip_h(self):
        self.overlay.flip_horizontal()
        self.flip_h_btn.setChecked(self.overlay.flip_h)
        self._update_rot_label()

    def _flip_v(self):
        self.overlay.flip_vertical()
        self.flip_v_btn.setChecked(self.overlay.flip_v)
        self._update_rot_label()

    def _update_rot_label(self):
        deg = int(self.overlay.rotation)
        self.rot_label.setText(f"{deg}\u00b0")

    def _apply_size(self):
        self.overlay.resize(self.w_spin.value(), self.h_spin.value())
        self._aspect_ratio = self.w_spin.value() / max(1, self.h_spin.value())
        self._sync_aspect_to_overlay()

    def _on_lock_aspect_toggled(self, checked: bool):
        if checked:
            self._aspect_ratio = self.w_spin.value() / max(1, self.h_spin.value())
        self._sync_aspect_to_overlay()

    def _on_w_changed(self, value: int):
        if self._updating_spin:
            return
        if self.lock_aspect_cb.isChecked() and self._aspect_ratio > 0:
            self._updating_spin = True
            self.h_spin.setValue(max(100, int(value / self._aspect_ratio)))
            self._updating_spin = False

    def _on_h_changed(self, value: int):
        if self._updating_spin:
            return
        if self.lock_aspect_cb.isChecked() and self._aspect_ratio > 0:
            self._updating_spin = True
            self.w_spin.setValue(max(100, int(value * self._aspect_ratio)))
            self._updating_spin = False

    def _toggle_lock_aspect(self):
        self.lock_aspect_cb.setChecked(not self.lock_aspect_cb.isChecked())
        # Refresh aspect ratio from current values when locking
        if self.lock_aspect_cb.isChecked():
            self._aspect_ratio = self.w_spin.value() / max(1, self.h_spin.value())
        self._sync_aspect_to_overlay()

    def _sync_aspect_to_overlay(self):
        """Keep overlay's aspect lock state in sync with the checkbox."""
        self.overlay.lock_aspect = self.lock_aspect_cb.isChecked()
        self.overlay.aspect_ratio = self._aspect_ratio

    def _fit_to_image(self):
        if self.overlay.image:
            screen = QApplication.primaryScreen().availableGeometry()
            w = min(self.overlay.image.width(), screen.width() - 50)
            h = min(self.overlay.image.height(), screen.height() - 50)
            self.overlay.resize(w, h)
            self._updating_spin = True
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)
            self._updating_spin = False
            self._aspect_ratio = w / max(1, h)
            self._sync_aspect_to_overlay()

    def closeEvent(self, event):
        self._save_settings()
        self.overlay.close()
        event.accept()


# ── Entry point ───────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    panel = ControlPanel()
    panel.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
