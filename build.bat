@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building executable...
pyinstaller --onefile --windowed --name GPU_VRAM_Monitor gpu_monitor.py

echo.
echo Build complete! Executable is in dist\GPU_VRAM_Monitor.exe
pause
