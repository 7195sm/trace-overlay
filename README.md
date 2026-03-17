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
- **Resizable Overlay** — Drag edges or set exact pixel dimensions
- **Always on Top** — Overlay stays above all other windows
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
2. **Open Image** — click the button or press `Ctrl+O`
3. **Adjust Opacity** — use the slider or `Ctrl+[` / `Ctrl+]`
4. **Position & Resize** — drag the overlay or its edges to fit your canvas
5. **Enable Click-Through** — press `Ctrl+T`, then draw freely in the app underneath
6. **Disable Click-Through** — press `Ctrl+T` again to reposition or resize

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open image |
| `Ctrl+T` | Toggle click-through mode |
| `Ctrl+H` | Hide / show overlay |
| `Ctrl+[` | Decrease opacity |
| `Ctrl+]` | Increase opacity |
| `Ctrl+F` | Fit overlay to original image size |

## Workflow Example

```
1. Open your drawing app (Paint, Clip Studio, Photoshop, etc.)
2. Launch Trace Overlay and load a reference image (Ctrl+O)
3. Set opacity to ~30-50% (Ctrl+[ or Ctrl+])
4. Position the overlay over your canvas
5. Enable click-through mode (Ctrl+T)
6. Start tracing!
```

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

Some ideas for future improvements:
- [ ] Image rotation and flip
- [ ] Multiple overlay windows
- [ ] Grid overlay option
- [ ] macOS support (alternative to Win32 click-through)
- [ ] Remember last window position and settings
- [ ] Drag-and-drop image loading

## License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

**Korean**: 그림 트레이싱 연습을 위한 반투명 오버레이 프로그램입니다. 이미지를 반투명하게 띄워두고 클릭 통과 모드를 켜면, 아래에 있는 그림판이나 클립스튜디오에서 바로 따라 그릴 수 있습니다.
