# Trace Overlay

A lightweight, always-on-top transparent image overlay for artists and designers.  
Load any image, make it semi-transparent, and trace over it in your favorite drawing app.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What It Does

Trace Overlay floats a semi-transparent image on top of everything on your screen. Enable **click-through mode**, and you can draw directly in the app underneath (MS Paint, Clip Studio, Photoshop, etc.) while seeing the reference image above.

Think of it as **digital tracing paper** for your monitor.

### Key Features

- **Click-Through Mode** — Mouse clicks pass through the overlay to the app below
- **Adjustable Opacity** — Slider from 5% to 100%
- **Zoom** — Ctrl+scroll to zoom at cursor position; wide range (10%–1000%)
- **Edge Detection** — Extract outlines only with Sobel filter (Ctrl+S)
- **Precise Rotation** — 0–360° slider + drag rotation handle on overlay
- **PPT-style Handles** — Resize handles at edges/corners, rotation handle at top
- **Flip** — Horizontal and vertical
- **Stretch & Resize** — Aspect ratio lock on/off; image stretches when off
- **Drag & Drop** — Drop image files directly onto the control panel
- **Arrow Key Nudge** — Fine-tune position (1 px / 20 px with Shift)
- **Reset All** — One button to reset position, size, rotation, zoom, and flip
- **Remembers Settings** — All settings saved and restored automatically
- **Lightweight** — Single Python file

## Quick Start

### Option 1: Download EXE (No Python needed)

Go to [**Releases**](../../releases) and download `TraceOverlay.exe`.

### Option 2: Run from Source

```bash
pip install PyQt5 Pillow
python trace_overlay.py
```

### Option 3: Build EXE Yourself

```bash
pip install PyQt5 Pillow pyinstaller
pyinstaller --onefile --windowed --name TraceOverlay trace_overlay.py
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open image |
| `Ctrl+T` | Toggle click-through mode |
| `Ctrl+H` | Hide / show overlay |
| `Ctrl+A` / `Ctrl+D` | Opacity down / up |
| `Ctrl+S` | Toggle edge detection |
| `Ctrl+Scroll` | Zoom at cursor position |
| `Ctrl+Q` / `Ctrl+E` | Rotate CCW / CW 2° |
| `Ctrl+W` | Reset rotation to 0° |
| `Ctrl+Shift+H` / `V` | Flip horizontal / vertical |
| `Ctrl+L` | Toggle aspect ratio lock |
| `Ctrl+F` | Reset all |
| Arrow keys | Nudge 1 px |
| Shift + arrows | Nudge 20 px |

## Requirements

- **OS**: Windows 10 / 11
- **Python**: 3.8+ (if running from source)
- **Dependencies**: PyQt5, Pillow

## License

[MIT License](LICENSE)

---

**Korean**: 그림 트레이싱 연습을 위한 반투명 오버레이 프로그램입니다. 이미지를 반투명하게 띄워두고 클릭 통과 모드를 켜면, 아래에 있는 그림판이나 클립스튜디오에서 바로 따라 그릴 수 있습니다.
