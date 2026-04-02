@echo off
:: Simple build script - run this on Windows with Python installed
pip install pynvml PySide6 psutil pyinstaller
pyinstaller --onefile --windowed --name GPU_VRAM_Monitor gpu_monitor.py
