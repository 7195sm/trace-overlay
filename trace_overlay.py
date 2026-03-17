"""
Trace Overlay v2.2.0 — Transparent image overlay for tracing practice.

Usage:
    pip install PyQt5 Pillow
    python trace_overlay.py

Platform: Windows 10/11 (click-through uses Win32 API)
"""

import sys, os, math, ctypes, json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QSlider, QSpinBox, QCheckBox,
    QVBoxLayout, QHBoxLayout, QFrame, QFileDialog, QMessageBox, QShortcut,
)
from PyQt5.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QUrl
from PyQt5.QtGui import (
    QPainter, QPixmap, QColor, QPen, QKeySequence, QTransform, QImage,
    QDragEnterEvent, QDropEvent, QBrush, QCursor,
)

try:
    from PIL import Image, ImageFilter, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# ── Constants ─────────────────────────────────────────────────
GWL_EXSTYLE   = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

EDGE_MARGIN    = 10
CORNER_MARGIN  = 16
OPACITY_STEP   = 5
ROTATION_STEP  = 2
ARROW_STEP     = 1
ARROW_SHIFT    = 20
HANDLE_R       = 5      # handle circle radius
ROT_HANDLE_Y   = 20     # rotation handle y inside overlay
ROT_STEM_TOP   = 4      # stem starts here (y)
ZOOM_MIN       = 0.1
ZOOM_MAX       = 10.0
ZOOM_WHEEL     = 0.1    # zoom step per wheel tick
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff"}
VERSION = "2.2.0"

SETTINGS_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "TraceOverlay"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
DEFAULTS = {
    "panel_x": 100, "panel_y": 100,
    "overlay_x": 200, "overlay_y": 100,
    "overlay_w": 800, "overlay_h": 600,
    "opacity": 50, "zoom": 100,
    "last_image": "", "rotation": 0,
    "flip_h": False, "flip_v": False,
    "lock_aspect": True, "edge_detect": False,
}

def load_settings():
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r") as f:
                return {**DEFAULTS, **json.load(f)}
    except Exception:
        pass
    return dict(DEFAULTS)

def save_settings(d):
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass

def qpixmap_to_pil(pm):
    qi = pm.toImage().convertToFormat(QImage.Format_RGBA8888)
    ptr = qi.bits(); ptr.setsize(qi.width() * qi.height() * 4)
    return Image.frombuffer("RGBA", (qi.width(), qi.height()), bytes(ptr), "raw", "RGBA", 0, 1)

def pil_to_qpixmap(img):
    img = img.convert("RGBA"); d = img.tobytes("raw", "RGBA")
    qi = QImage(d, img.width, img.height, img.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qi.copy())

def apply_edge_detection(pm):
    if not HAS_PILLOW: return pm
    return pil_to_qpixmap(ImageOps.invert(qpixmap_to_pil(pm).convert("L").filter(ImageFilter.FIND_EDGES)).convert("RGBA"))


# ══════════════════════════════════════════════════════════════
class OverlayWindow(QWidget):
# ══════════════════════════════════════════════════════════════
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.image = None
        self.opacity_value = 0.5
        self._rot = 0.0
        self._flip_h = self._flip_v = False
        self.lock_aspect = True
        self.aspect_ratio = 4/3
        self.zoom = 1.0
        self.pan_x = self.pan_y = 0.0   # pixel offset of image center

        self._click_through = False
        self._dragging = self._resizing = self._rot_dragging = False
        self._drag_start = QPoint()
        self._resize_edge = ""
        self._start_geom = QRect()

        self.setWindowTitle("Trace Overlay")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(100, 100)
        self.resize(800, 600)

    # ── properties ───────────────────────────────────────────
    @property
    def rotation(self): return self._rot
    @property
    def flip_h(self): return self._flip_h
    @property
    def flip_v(self): return self._flip_v

    def set_click_through(self, on):
        if sys.platform != "win32": return
        self._click_through = on
        hwnd = int(self.winId())
        s = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if on:  s |= WS_EX_LAYERED | WS_EX_TRANSPARENT
        else:   s = (s & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, s)
        self.update()

    def set_image(self, pm):  self.image = pm; self.update()
    def set_opacity(self, v): self.opacity_value = max(.05, min(1., v)); self.update()
    def set_rotation(self, d): self._rot = d % 360; self.update()
    def rotate_by(self, d):   self.set_rotation(self._rot + d)
    def flip_horizontal(self): self._flip_h = not self._flip_h; self.update()
    def flip_vertical(self):   self._flip_v = not self._flip_v; self.update()
    def set_transform(self, r, fh, fv):
        self._rot = r % 360; self._flip_h = fh; self._flip_v = fv; self.update()

    def set_zoom(self, z):
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, z)); self.update()

    def zoom_at(self, factor, mx, my):
        """Zoom so the point under (mx, my) stays fixed."""
        old_z = self.zoom
        new_z = max(ZOOM_MIN, min(ZOOM_MAX, old_z * factor))
        if new_z == old_z: return
        cx, cy = self.width()/2, self.height()/2
        r = new_z / old_z
        self.pan_x = (mx - cx) * (1 - r) + r * self.pan_x
        self.pan_y = (my - cy) * (1 - r) + r * self.pan_y
        self.zoom = new_z
        self.update()

    # ── handle positions ─────────────────────────────────────
    def _handle_points(self):
        """8 resize handles + 1 rotation handle (index 8)."""
        w, h = self.width(), self.height()
        return [
            QPointF(0, 0), QPointF(w/2, 0), QPointF(w, 0),        # top L, C, R
            QPointF(0, h/2), QPointF(w, h/2),                      # mid L, R
            QPointF(0, h), QPointF(w/2, h), QPointF(w, h),         # bot L, C, R
            QPointF(w/2, ROT_HANDLE_Y),                             # rotation handle
        ]

    def _hit_handle(self, pos, radius=12):
        pts = self._handle_points()
        for i, p in enumerate(pts):
            if (pos.x()-p.x())**2 + (pos.y()-p.y())**2 <= radius**2:
                return i
        return -1

    # ── painting ─────────────────────────────────────────────
    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)

        if not self._click_through:
            # Border
            p.setPen(QPen(QColor(120, 120, 120, 180), 1, Qt.SolidLine))
            p.drawRect(0, 0, self.width()-1, self.height()-1)

            # Handles
            pts = self._handle_points()
            handle_pen = QPen(QColor(120, 120, 120, 220), 1.5)
            handle_brush = QBrush(QColor(255, 255, 255, 240))
            p.setPen(handle_pen); p.setBrush(handle_brush)
            for i, pt in enumerate(pts):
                p.drawEllipse(pt, HANDLE_R, HANDLE_R)

            # Rotation handle stem
            rot_pt = pts[8]
            top_center = QPointF(self.width()/2, ROT_STEM_TOP)
            p.setPen(QPen(QColor(120, 120, 120, 180), 1.5))
            p.drawLine(top_center, rot_pt)

            # Rotation arrow icon
            p.setPen(QPen(QColor(80, 80, 80, 200), 1.5))
            rc = rot_pt
            p.drawArc(int(rc.x())-4, int(rc.y())-4, 8, 8, 30*16, 300*16)

        # Image
        if self.image:
            p.setOpacity(self.opacity_value)

            if self.lock_aspect:
                scaled = self.image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                scaled = self.image.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

            cx, cy = self.width()/2, self.height()/2

            p.save()
            p.translate(cx + self.pan_x, cy + self.pan_y)
            p.scale(self.zoom, self.zoom)
            p.rotate(self._rot)
            sx = -1.0 if self._flip_h else 1.0
            sy = -1.0 if self._flip_v else 1.0
            p.scale(sx, sy)
            p.drawPixmap(-scaled.width()//2, -scaled.height()//2, scaled)
            p.restore()

        p.end()

    # ── mouse interaction ────────────────────────────────────
    def _edge_at(self, pos):
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        E = EDGE_MARGIN; edges = ""
        if y < E: edges += "t"
        elif y > h-E: edges += "b"
        if x < E: edges += "l"
        elif x > w-E: edges += "r"
        return edges

    def _cursor_for_zone(self, pos):
        # Check rotation handle first
        hit = self._hit_handle(pos)
        if hit == 8:
            return Qt.CrossCursor

        edges = self._edge_at(pos)
        m = {"t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
             "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor,
             "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
             "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor}
        return m.get(edges, Qt.ArrowCursor)

    def mousePressEvent(self, ev):
        if self._click_through or ev.button() != Qt.LeftButton: return

        # Rotation handle?
        if self._hit_handle(ev.pos()) == 8:
            self._rot_dragging = True
            return

        edges = self._edge_at(ev.pos())
        if edges:
            self._resizing = True; self._resize_edge = edges
            self._drag_start = ev.globalPos(); self._start_geom = self.geometry()
        else:
            self._dragging = True
            self._drag_start = ev.globalPos() - self.pos()

    def mouseMoveEvent(self, ev):
        if self._click_through: return

        if self._rot_dragging:
            cx, cy = self.width()/2, self.height()/2
            dx, dy = ev.pos().x() - cx, ev.pos().y() - cy
            angle = math.degrees(math.atan2(dx, -dy)) % 360
            self.set_rotation(angle)
            self.panel._sync_rotation_from_overlay()
            return

        if self._dragging:
            self.move(ev.globalPos() - self._drag_start)
        elif self._resizing:
            self._do_resize(ev.globalPos())
        else:
            self.setCursor(self._cursor_for_zone(ev.pos()))

    def mouseReleaseEvent(self, ev):
        self._dragging = self._resizing = self._rot_dragging = False
        self._resize_edge = ""

    def _do_resize(self, gp):
        dx = gp.x() - self._drag_start.x()
        dy = gp.y() - self._drag_start.y()
        g = QRect(self._start_geom)
        mw, mh = self.minimumWidth(), self.minimumHeight()
        e = self._resize_edge

        if "r" in e: g.setWidth(max(mw, g.width()+dx))
        if "b" in e: g.setHeight(max(mh, g.height()+dy))
        if "l" in e:
            nl = g.left()+dx
            if g.right()-nl >= mw: g.setLeft(nl)
        if "t" in e:
            nt = g.top()+dy
            if g.bottom()-nt >= mh: g.setTop(nt)

        if self.lock_aspect and self.aspect_ratio > 0:
            hh = ("l" in e or "r" in e); hv = ("t" in e or "b" in e)
            if hh and not hv: g.setHeight(max(mh, int(g.width()/self.aspect_ratio)))
            elif hv and not hh: g.setWidth(max(mw, int(g.height()*self.aspect_ratio)))
            elif hh and hv: g.setHeight(max(mh, int(g.width()/self.aspect_ratio)))

        self.setGeometry(g)

    # ── keyboard ─────────────────────────────────────────────
    def keyPressEvent(self, ev):
        s = ARROW_SHIFT if ev.modifiers() & Qt.ShiftModifier else ARROW_STEP
        k = ev.key()
        if   k == Qt.Key_Left:  self.move(self.x()-s, self.y())
        elif k == Qt.Key_Right: self.move(self.x()+s, self.y())
        elif k == Qt.Key_Up:    self.move(self.x(), self.y()-s)
        elif k == Qt.Key_Down:  self.move(self.x(), self.y()+s)
        else: super().keyPressEvent(ev)

    # ── mouse wheel → zoom ───────────────────────────────────
    def wheelEvent(self, ev):
        if not (ev.modifiers() & Qt.ControlModifier):
            super().wheelEvent(ev); return
        if not self.image: return
        delta = ev.angleDelta().y()
        if delta == 0: return
        factor = 1.0 + ZOOM_WHEEL if delta > 0 else 1.0 / (1.0 + ZOOM_WHEEL)
        pos = ev.pos()
        self.zoom_at(factor, pos.x(), pos.y())
        self.panel._sync_zoom_from_overlay()


# ══════════════════════════════════════════════════════════════
class ControlPanel(QWidget):
# ══════════════════════════════════════════════════════════════
    STYLE = """
        QWidget { font-family:'Segoe UI','Malgun Gothic',sans-serif; font-size:13px; }
        QPushButton { padding:7px 14px; border:1px solid #ccc; border-radius:4px;
                      background:#f5f5f5; min-height:28px; }
        QPushButton:hover { background:#e8e8e8; }
        QPushButton:pressed { background:#ddd; }
        QPushButton:checked { background:#d0e8ff; border-color:#4a9eff; color:#0060c0; }
        QSlider::groove:horizontal { height:6px; background:#ddd; border-radius:3px; }
        QSlider::handle:horizontal { width:16px; height:16px; margin:-5px 0;
                                     background:#4a9eff; border-radius:8px; }
        QSpinBox { padding:4px 6px; border:1px solid #ccc; border-radius:3px; min-height:24px; }
        QCheckBox { spacing:6px; }
    """

    def __init__(self):
        super().__init__()
        self.overlay = OverlayWindow(self)
        self._img_path = ""
        self._orig_img = None
        self._edge_img = None
        self._ar = 4/3
        self._spin_lock = False
        self._edge_mode = False
        self._settings = load_settings()
        self._build_ui()
        self._setup_shortcuts()
        self._restore()

    # ── drag & drop ──────────────────────────────────────────
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            for u in ev.mimeData().urls():
                if u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in IMAGE_EXTS:
                    ev.acceptProposedAction(); return

    def dropEvent(self, ev):
        for u in ev.mimeData().urls():
            if u.isLocalFile():
                p = u.toLocalFile()
                if Path(p).suffix.lower() in IMAGE_EXTS:
                    self._load_image(p); return

    # ── build UI ─────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Trace Overlay")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedWidth(420); self.setAcceptDrops(True)
        self.setStyleSheet(self.STYLE)

        R = QVBoxLayout(); R.setContentsMargins(16,16,16,16); R.setSpacing(10)

        # Title
        t = QLabel("Trace Overlay")
        t.setStyleSheet("font-size:20px; font-weight:bold; color:#333;")
        R.addWidget(t)
        R.addWidget(self._lbl("Transparent image overlay for tracing practice", "#888", 11))
        R.addWidget(self._sep())

        # Open
        self.open_btn = QPushButton("Open Image  (Ctrl+O)")
        self.open_btn.setStyleSheet(self.open_btn.styleSheet()+"font-size:14px; padding:10px 14px;")
        self.open_btn.clicked.connect(self._open_image); R.addWidget(self.open_btn)
        self.file_label = self._lbl("No image loaded  (or drag && drop here)", "gray", 11)
        self.file_label.setWordWrap(True); R.addWidget(self.file_label)
        R.addWidget(self._sep())

        # Opacity
        R.addWidget(QLabel("Opacity  (Ctrl+A / Ctrl+D)"))
        h = QHBoxLayout()
        self.opa_slider = QSlider(Qt.Horizontal); self.opa_slider.setRange(5,100); self.opa_slider.setValue(50)
        self.opa_slider.valueChanged.connect(self._on_opacity); h.addWidget(self.opa_slider)
        self.opa_lbl = QLabel("50%"); self.opa_lbl.setFixedWidth(44)
        self.opa_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter); h.addWidget(self.opa_lbl)
        R.addLayout(h); R.addWidget(self._sep())

        # Click-through
        self.ct_btn = QPushButton("Enable Click-Through  (Ctrl+T)")
        self.ct_btn.setCheckable(True); self.ct_btn.toggled.connect(self._toggle_ct); R.addWidget(self.ct_btn)
        R.addWidget(self._lbl("ON \u2192 clicks pass through  |  OFF \u2192 move / resize", "#999", 10))
        R.addWidget(self._sep())

        # Edge
        self.edge_btn = QPushButton("Edge Detection  (Ctrl+S)")
        self.edge_btn.setCheckable(True); self.edge_btn.toggled.connect(self._toggle_edge)
        if not HAS_PILLOW: self.edge_btn.setEnabled(False); self.edge_btn.setToolTip("pip install Pillow")
        R.addWidget(self.edge_btn); R.addWidget(self._sep())

        # Zoom
        R.addWidget(QLabel("Zoom  (Ctrl+Scroll on overlay)"))
        zh = QHBoxLayout()
        self.zoom_slider = QSlider(Qt.Horizontal); self.zoom_slider.setRange(10, 1000); self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider); zh.addWidget(self.zoom_slider)
        self.zoom_lbl = QLabel("100%"); self.zoom_lbl.setFixedWidth(52)
        self.zoom_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter); zh.addWidget(self.zoom_lbl)
        R.addLayout(zh); R.addWidget(self._sep())

        # Rotation
        R.addWidget(QLabel("Rotation  (Ctrl+Q / Ctrl+E, 2\u00b0)"))
        rh = QHBoxLayout()
        self.rot_slider = QSlider(Qt.Horizontal); self.rot_slider.setRange(0,360); self.rot_slider.setValue(0)
        self.rot_slider.valueChanged.connect(self._on_rot_slider); rh.addWidget(self.rot_slider)
        self.rot_lbl = QLabel("0\u00b0"); self.rot_lbl.setFixedWidth(44)
        self.rot_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter); rh.addWidget(self.rot_lbl)
        R.addLayout(rh)

        xr = QHBoxLayout(); xr.setSpacing(6)
        b = QPushButton("\u21b6  -90\u00b0"); b.clicked.connect(lambda: self._rot_by(-90)); xr.addWidget(b)
        b = QPushButton("+90\u00b0  \u21b7"); b.clicked.connect(lambda: self._rot_by(90)); xr.addWidget(b)
        b = QPushButton("0\u00b0"); b.setFixedWidth(42); b.clicked.connect(self._rot_reset); xr.addWidget(b)
        self.fh_btn = QPushButton("\u2194  Flip H"); self.fh_btn.setCheckable(True); self.fh_btn.clicked.connect(self._flip_h); xr.addWidget(self.fh_btn)
        self.fv_btn = QPushButton("\u2195  Flip V"); self.fv_btn.setCheckable(True); self.fv_btn.clicked.connect(self._flip_v); xr.addWidget(self.fv_btn)
        R.addLayout(xr)
        R.addWidget(self._lbl("Drag rotation handle on overlay to rotate freely", "#999", 10, Qt.AlignCenter))
        R.addWidget(self._sep())

        # Size
        R.addWidget(QLabel("Overlay Size"))
        self.lock_cb = QCheckBox("Lock aspect ratio  (Ctrl+L)")
        self.lock_cb.setChecked(True); self.lock_cb.toggled.connect(self._on_lock_toggled); R.addWidget(self.lock_cb)
        sh = QHBoxLayout(); sh.setSpacing(6)
        self.w_spin = self._spin(800); self.w_spin.valueChanged.connect(self._on_w); self.w_spin.editingFinished.connect(self._apply_size)
        sh.addWidget(self.w_spin); sh.addWidget(QLabel("\u00d7"))
        self.h_spin = self._spin(600); self.h_spin.valueChanged.connect(self._on_h); self.h_spin.editingFinished.connect(self._apply_size)
        sh.addWidget(self.h_spin)
        ab = QPushButton("Apply"); ab.setFixedWidth(60); ab.clicked.connect(self._apply_size); sh.addWidget(ab)
        R.addLayout(sh)

        self.reset_btn = QPushButton("Reset All  (Ctrl+F)")
        self.reset_btn.clicked.connect(self._reset_all); self.reset_btn.setEnabled(False); R.addWidget(self.reset_btn)
        R.addWidget(self._sep())

        # Shortcuts reference
        sc = (
            "Ctrl+O              Open image\n"
            "Ctrl+T              Toggle click-through\n"
            "Ctrl+H              Hide / show overlay\n"
            "Ctrl+A / D           Opacity down / up\n"
            "Ctrl+S              Edge detection\n"
            "Ctrl+Scroll          Zoom at cursor\n"
            "Ctrl+Q / E           Rotate CCW / CW 2\u00b0\n"
            "Ctrl+W              Reset rotation\n"
            "Ctrl+Shift+H / V     Flip H / V\n"
            "Ctrl+L              Lock aspect ratio\n"
            "Ctrl+F              Reset all\n"
            "\u2190\u2191\u2192\u2193 / Shift+\u2190\u2191\u2192\u2193    Nudge 1 / 20 px"
        )
        sl = QLabel(sc); sl.setStyleSheet("color:#888; font-size:10px; font-family:'Consolas','Courier New',monospace;")
        R.addWidget(sl)
        R.addStretch()
        R.addWidget(self._lbl(f"v{VERSION}  \u00b7  Closing this panel closes the overlay", "#aaa", 10, Qt.AlignCenter))
        self.setLayout(R)

    # ── helpers ──────────────────────────────────────────────
    @staticmethod
    def _sep():
        f = QFrame(); f.setFrameShape(QFrame.HLine); f.setStyleSheet("color:#e0e0e0;"); return f

    @staticmethod
    def _lbl(txt, color, size, align=None):
        l = QLabel(txt); l.setStyleSheet(f"color:{color}; font-size:{size}px;")
        if align: l.setAlignment(align)
        return l

    @staticmethod
    def _spin(val):
        s = QSpinBox(); s.setRange(100,4000); s.setValue(val); s.setSuffix("  px"); return s

    # ── shortcuts ────────────────────────────────────────────
    def _setup_shortcuts(self):
        B = {
            "Ctrl+O": self._open_image,
            "Ctrl+T": lambda: self.ct_btn.toggle(),
            "Ctrl+H": self._toggle_vis,
            "Ctrl+A": self._opa_dn, "Ctrl+D": self._opa_up,
            "Ctrl+S": lambda: self.edge_btn.toggle() if self.edge_btn.isEnabled() else None,
            "Ctrl+Q": lambda: self._rot_by(-ROTATION_STEP),
            "Ctrl+E": lambda: self._rot_by(ROTATION_STEP),
            "Ctrl+W": self._rot_reset,
            "Ctrl+Shift+H": self._flip_h, "Ctrl+Shift+V": self._flip_v,
            "Ctrl+L": lambda: self.lock_cb.setChecked(not self.lock_cb.isChecked()),
            "Ctrl+F": self._reset_all,
        }
        for k, fn in B.items():
            QShortcut(QKeySequence(k), self).activated.connect(fn)
            QShortcut(QKeySequence(k), self.overlay).activated.connect(fn)

    # ── settings ─────────────────────────────────────────────
    def _restore(self):
        s = self._settings
        self.move(s["panel_x"], s["panel_y"])
        self.overlay.move(s["overlay_x"], s["overlay_y"])
        self.overlay.resize(s["overlay_w"], s["overlay_h"])
        self._spin_lock = True
        self.w_spin.setValue(s["overlay_w"]); self.h_spin.setValue(s["overlay_h"])
        self._spin_lock = False
        self.opa_slider.setValue(s["opacity"])
        self.zoom_slider.setValue(s.get("zoom", 100))
        self.lock_cb.setChecked(s.get("lock_aspect", True))
        self._ar = s["overlay_w"] / max(1, s["overlay_h"])
        self._sync_aspect()

        last = s.get("last_image", "")
        if last and os.path.isfile(last):
            self._load_image(last)
            self.overlay.set_transform(s.get("rotation",0), s.get("flip_h",False), s.get("flip_v",False))
            self.rot_slider.setValue(int(s.get("rotation",0)) % 361)
            self.fh_btn.setChecked(s.get("flip_h",False)); self.fv_btn.setChecked(s.get("flip_v",False))
            self._update_rot_lbl()
            if s.get("edge_detect",False) and HAS_PILLOW: self.edge_btn.setChecked(True)

    def _save(self):
        p, op = self.pos(), self.overlay.pos()
        save_settings({
            "panel_x":p.x(),"panel_y":p.y(),"overlay_x":op.x(),"overlay_y":op.y(),
            "overlay_w":self.overlay.width(),"overlay_h":self.overlay.height(),
            "opacity":self.opa_slider.value(), "zoom":self.zoom_slider.value(),
            "last_image":self._img_path, "rotation":self.overlay.rotation,
            "flip_h":self.overlay.flip_h, "flip_v":self.overlay.flip_v,
            "lock_aspect":self.lock_cb.isChecked(), "edge_detect":self._edge_mode,
        })

    # ── image ────────────────────────────────────────────────
    def _load_image(self, path):
        pm = QPixmap(path)
        if pm.isNull(): QMessageBox.warning(self,"Error","Could not load."); return
        self._img_path = path; self._orig_img = pm; self._edge_img = None
        self._edge_mode = False; self.edge_btn.setChecked(False)
        self.overlay.set_image(pm)
        self.overlay.pan_x = self.overlay.pan_y = 0.0
        self.overlay.zoom = 1.0; self.zoom_slider.setValue(100)

        sc = QApplication.primaryScreen().availableGeometry()
        w = min(pm.width(), sc.width()-50); h = min(pm.height(), sc.height()-50)
        self.overlay.resize(w, h)
        self._spin_lock = True; self.w_spin.setValue(w); self.h_spin.setValue(h); self._spin_lock = False
        self.overlay.show(); self.reset_btn.setEnabled(True)
        self._ar = w / max(1, h); self._sync_aspect()
        self.overlay.set_transform(0, False, False)
        self.rot_slider.setValue(0); self.fh_btn.setChecked(False); self.fv_btn.setChecked(False)
        self._update_rot_lbl()
        self.file_label.setText(f"{os.path.basename(path)}  ({pm.width()} \u00d7 {pm.height()} px)")

    # ── slots ────────────────────────────────────────────────
    def _open_image(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;All Files (*)")
        if p: self._load_image(p)

    def _on_opacity(self, v): self.opa_lbl.setText(f"{v}%"); self.overlay.set_opacity(v/100.)
    def _opa_dn(self): self.opa_slider.setValue(max(5, self.opa_slider.value()-OPACITY_STEP))
    def _opa_up(self): self.opa_slider.setValue(min(100, self.opa_slider.value()+OPACITY_STEP))

    def _toggle_ct(self, on):
        self.overlay.set_click_through(on)
        self.ct_btn.setText(("Disable" if on else "Enable")+"  Click-Through  (Ctrl+T)")

    def _toggle_vis(self):
        self.overlay.hide() if self.overlay.isVisible() else self.overlay.show()

    def _toggle_edge(self, on):
        if not self._orig_img: return
        self._edge_mode = on
        if on:
            if not self._edge_img: self._edge_img = apply_edge_detection(self._orig_img)
            self.overlay.set_image(self._edge_img)
        else:
            self.overlay.set_image(self._orig_img)

    # zoom
    def _on_zoom_slider(self, v):
        self.zoom_lbl.setText(f"{v}%")
        self.overlay.pan_x = self.overlay.pan_y = 0.0  # center zoom from slider
        self.overlay.set_zoom(v / 100.)

    def _sync_zoom_from_overlay(self):
        v = int(self.overlay.zoom * 100)
        self.zoom_slider.blockSignals(True); self.zoom_slider.setValue(v); self.zoom_slider.blockSignals(False)
        self.zoom_lbl.setText(f"{v}%")

    # rotation
    def _on_rot_slider(self, v):
        self.overlay.set_rotation(float(v % 360)); self._update_rot_lbl()

    def _rot_by(self, d):
        nr = (self.overlay.rotation + d) % 360; self.rot_slider.setValue(int(nr))

    def _rot_reset(self): self.rot_slider.setValue(0)

    def _sync_rotation_from_overlay(self):
        d = int(self.overlay.rotation)
        self.rot_slider.blockSignals(True); self.rot_slider.setValue(d); self.rot_slider.blockSignals(False)
        self._update_rot_lbl()

    def _flip_h(self): self.overlay.flip_horizontal(); self.fh_btn.setChecked(self.overlay.flip_h)
    def _flip_v(self): self.overlay.flip_vertical(); self.fv_btn.setChecked(self.overlay.flip_v)
    def _update_rot_lbl(self): self.rot_lbl.setText(f"{int(self.overlay.rotation)}\u00b0")

    # size
    def _apply_size(self):
        self.overlay.resize(self.w_spin.value(), self.h_spin.value())
        self._ar = self.w_spin.value() / max(1, self.h_spin.value())
        self._sync_aspect()

    def _on_w(self, v):
        if self._spin_lock: return
        if self.lock_cb.isChecked() and self._ar > 0:
            self._spin_lock = True; self.h_spin.setValue(max(100, int(v/self._ar))); self._spin_lock = False

    def _on_h(self, v):
        if self._spin_lock: return
        if self.lock_cb.isChecked() and self._ar > 0:
            self._spin_lock = True; self.w_spin.setValue(max(100, int(v*self._ar))); self._spin_lock = False

    def _on_lock_toggled(self, on):
        if on: self._ar = self.w_spin.value() / max(1, self.h_spin.value())
        self._sync_aspect()

    def _sync_aspect(self):
        self.overlay.lock_aspect = self.lock_cb.isChecked()
        self.overlay.aspect_ratio = self._ar

    # reset
    def _reset_all(self):
        if not self.overlay.image: return
        self.overlay.set_transform(0, False, False)
        self.rot_slider.setValue(0); self.fh_btn.setChecked(False); self.fv_btn.setChecked(False)
        self._update_rot_lbl()
        self.overlay.pan_x = self.overlay.pan_y = 0.0
        self.overlay.zoom = 1.0; self.zoom_slider.setValue(100)

        img = self._orig_img or self.overlay.image
        sc = QApplication.primaryScreen().availableGeometry()
        w = min(img.width(), sc.width()-50); h = min(img.height(), sc.height()-50)
        self.overlay.resize(w, h)
        self._spin_lock = True; self.w_spin.setValue(w); self.h_spin.setValue(h); self._spin_lock = False
        self._ar = w / max(1, h); self._sync_aspect()
        self.overlay.move(sc.x()+(sc.width()-w)//2, sc.y()+(sc.height()-h)//2)

    def closeEvent(self, ev):
        self._save(); self.overlay.close(); ev.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    ControlPanel().show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
