@echo off
echo ============================================
echo   Trace Overlay - EXE Builder
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Download from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install!
    pause
    exit /b 1
)

echo [1/3] Installing packages...
pip install PyQt5 Pillow pyinstaller --quiet

echo [2/3] Building EXE... (takes 1-2 min)
pyinstaller --noconfirm --onefile --windowed --name "TraceOverlay" --hidden-import PIL --hidden-import PIL.Image --hidden-import PIL.ImageFilter --hidden-import PIL.ImageOps --clean trace_overlay.py

echo.
if exist "dist\TraceOverlay.exe" (
    echo ============================================
    echo   BUILD SUCCESS!
    echo   dist\TraceOverlay.exe is ready.
    echo ============================================
    echo.
    echo Opening dist folder...
    explorer dist
) else (
    echo [ERROR] Build failed. Check the error messages above.
)

pause
