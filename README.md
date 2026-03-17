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

- **Click-Through Mode** — Mouse clicks pass through the overlay to the app below (Windows API)
- **Adjustable Opacity** — Slider from 5% to 100%
- **Rotation & Flip** — Precise 0–359° rotation slider, quick ±90° buttons, flip horizontal/vertical
- **Drag & Drop** — Drop an image file onto the control panel to load it
- **Resizable Overlay** — Drag edges or set exact pixel dimensions
- **Aspect Ratio Lock** — Keep proportions when resizing (toggle with checkbox or `Ctrl+L`)
- **Always on Top** — Overlay stays above all other windows
- **Remembers Settings** — Window positions, opacity, last image, and transform are saved automatically
- **Keyboard Shortcuts** — Control everything without leaving your drawing app
- **Lightweight** — Single Python file, minimal dependencies

## Quick Start

### Option 1: Download EXE (No Python needed)

Go to [**Releases**](../../releases) and download `TraceOverlay.exe`.  
Double-click and you're ready to go.

### Option 2: Run from Source

```bash
pip install PyQt5
python trace_overlay.py
```

### Option 3: Build EXE Yourself

```bash
pip install PyQt5 pyinstaller
pyinstaller --onefile --windowed --name TraceOverlay trace_overlay.py
```

The executable will be in the `dist/` folder.

## How to Use

1. **Launch** the app — a small control panel appears
2. **Open Image** — click the button, press `Ctrl+O`, or drag & drop an image file
3. **Adjust Opacity** — use the slider or `Ctrl+[` / `Ctrl+]`
4. **Position & Resize** — drag the overlay or its edges to fit your canvas
5. **Rotate / Flip** — use the buttons or keyboard shortcuts to transform the image
6. **Enable Click-Through** — press `Ctrl+T`, then draw freely in the app underneath
7. **Close** — all settings (positions, opacity, image, transform) are saved automatically

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open image |
| `Ctrl+T` | Toggle click-through mode |
| `Ctrl+H` | Hide / show overlay |
| `Ctrl+[` | Decrease opacity |
| `Ctrl+]` | Increase opacity |
| `Ctrl+R` | Rotate clockwise 2° |
| `Ctrl+Shift+R` | Rotate counter-clockwise 2° |
| `Ctrl+Shift+H` | Flip horizontal |
| `Ctrl+Shift+V` | Flip vertical |
| `Ctrl+F` | Fit overlay to original image size |
| `Ctrl+L` | Toggle aspect ratio lock |

## Settings

Settings are saved automatically when you close the app to:  
`%APPDATA%\TraceOverlay\settings.json`

Saved data includes: panel position, overlay position & size, opacity, last loaded image path, and rotation/flip state.

## Requirements

- **OS**: Windows 10 / 11 (click-through uses Win32 API)
- **Python**: 3.8+ (if running from source)
- **Dependencies**: PyQt5

## Project Structure

```
trace-overlay/
├── trace_overlay.py      # Main application (single file)
├── build.bat             # One-click EXE builder for Windows
├── requirements.txt
├── LICENSE
└── .github/
    └── workflows/
        └── build.yml     # Auto-build EXE on GitHub Release
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

**Korean**: 그림 트레이싱 연습을 위한 반투명 오버레이 프로그램입니다. 이미지를 반투명하게 띄워두고 클릭 통과 모드를 켜면, 아래에 있는 그림판이나 클립스튜디오에서 바로 따라 그릴 수 있습니다.
