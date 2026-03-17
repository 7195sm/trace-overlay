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
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSlider, QSpinBox,
    QVBoxLayout, QHBoxLayout, QFrame, QFileDialog, QMessageBox, QSizeGrip,
)
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QPixmap, QColor, QPen, QCursor, QIcon

# ── Win32 constants ───────────────────────────────────────────
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

EDGE_MARGIN = 8  # px — resize handle detection zone

VERSION = "1.0.0"


class OverlayWindow(QWidget):
    """Frameless, always-on-top transparent overlay that displays an image."""

    def __init__(self):
        super().__init__()
        self.image: QPixmap | None = None
        self.opacity_value: float = 0.5
        self._click_through: bool = False
        self._dragging: bool = False
        self._resizing: bool = False
        self._drag_start: QPoint = QPoint()
        self._resize_edge: str = ""
        self._start_geometry: QRect = QRect()

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
        self.update()

    def set_opacity(self, value: float):
        self.opacity_value = value
        self.update()

    # ── Painting ─────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if not self._click_through:
            # Edit mode: show light background + dashed border
            painter.fillRect(self.rect(), QColor(40, 40, 40, 25))
            painter.setPen(QPen(QColor(0, 120, 255, 120), 2, Qt.DashLine))
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        else:
            # Click-through mode: subtle border only
            painter.setPen(QPen(QColor(100, 100, 100, 40), 1))
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        if self.image:
            painter.setOpacity(self.opacity_value)
            scaled = self.image.scaled(
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
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("Trace Overlay")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedWidth(330)
        self.setStyleSheet(self.STYLE)

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
        self.open_btn = QPushButton("Open Image")
        self.open_btn.setStyleSheet(
            self.open_btn.styleSheet()
            + "font-size: 14px; padding: 10px;"
        )
        self.open_btn.clicked.connect(self._open_image)
        root.addWidget(self.open_btn)

        self.file_label = QLabel("No image loaded")
        self.file_label.setStyleSheet("color: gray; font-size: 11px;")
        self.file_label.setWordWrap(True)
        root.addWidget(self.file_label)

        root.addWidget(self._sep())

        # ── Opacity ──
        root.addWidget(QLabel("Opacity"))
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
        self.lock_btn = QPushButton("Enable Click-Through")
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

        # ── Size controls ──
        root.addWidget(QLabel("Overlay Size"))
        size_row = QHBoxLayout()
        self.w_spin = QSpinBox()
        self.w_spin.setRange(100, 4000)
        self.w_spin.setValue(800)
        self.w_spin.setSuffix(" px")
        size_row.addWidget(self.w_spin)
        size_row.addWidget(QLabel("\u00d7"))
        self.h_spin = QSpinBox()
        self.h_spin.setRange(100, 4000)
        self.h_spin.setValue(600)
        self.h_spin.setSuffix(" px")
        size_row.addWidget(self.h_spin)
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(50)
        apply_btn.clicked.connect(self._apply_size)
        size_row.addWidget(apply_btn)
        root.addLayout(size_row)

        self.fit_btn = QPushButton("Fit to Original Image Size")
        self.fit_btn.clicked.connect(self._fit_to_image)
        self.fit_btn.setEnabled(False)
        root.addWidget(self.fit_btn)

        root.addStretch()

        # ── Footer ──
        footer = QLabel(f"v{VERSION}  \u00b7  Closing this panel closes the overlay")
        footer.setStyleSheet("color: #aaa; font-size: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

        self.setLayout(root)

    @staticmethod
    def _sep() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        return line

    # ── Slots ─────────────────────────────────────────────────
    def _open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;All Files (*)",
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Error", "Could not load this image.")
            return

        self.overlay.set_image(pixmap)

        # Constrain to screen size
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(pixmap.width(), screen.width() - 50)
        h = min(pixmap.height(), screen.height() - 50)
        self.overlay.resize(w, h)
        self.w_spin.setValue(w)
        self.h_spin.setValue(h)

        self.overlay.show()
        self.fit_btn.setEnabled(True)

        name = os.path.basename(path)
        self.file_label.setText(f"{name}  ({pixmap.width()} \u00d7 {pixmap.height()} px)")

    def _on_opacity(self, value: int):
        self.opacity_label.setText(f"{value}%")
        self.overlay.set_opacity(value / 100.0)

    def _toggle_click_through(self, checked: bool):
        self.overlay.set_click_through(checked)
        if checked:
            self.lock_btn.setText("Disable Click-Through")
        else:
            self.lock_btn.setText("Enable Click-Through")

    def _apply_size(self):
        self.overlay.resize(self.w_spin.value(), self.h_spin.value())

    def _fit_to_image(self):
        if self.overlay.image:
            screen = QApplication.primaryScreen().availableGeometry()
            w = min(self.overlay.image.width(), screen.width() - 50)
            h = min(self.overlay.image.height(), screen.height() - 50)
            self.overlay.resize(w, h)
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)

    def closeEvent(self, event):
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
