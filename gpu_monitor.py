import sys
import time
from datetime import datetime

import pynvml

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QFont, QColor, QPalette
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QPushButton,
        QGroupBox,
    )
except ImportError:
    print("PySide6 not installed. Run: pip install PySide6")
    sys.exit(1)


class GPUMonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPU VRAM Monitor")
        self.setMinimumSize(700, 400)
        
        pynvml.nvmlInit()
        self.device_count = pynvml.nvmlDeviceGetCount()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.gpu_info_label = QLabel()
        self.gpu_info_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(self.gpu_info_label)
        
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(4)
        self.process_table.setHorizontalHeaderLabels(["PID", "Process Name", "VRAM Usage", "GPU"])
        self.process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.process_table.verticalHeader().setVisible(False)
        self.process_table.setAlternatingRowColors(True)
        layout.addWidget(self.process_table)
        
        controls_layout = QHBoxLayout()
        
        self.refresh_label = QLabel("Auto-refresh: ON (2s)")
        controls_layout.addWidget(self.refresh_label)
        
        self.refresh_btn = QPushButton("Refresh Now")
        self.refresh_btn.clicked.connect(self.update_gpu_info)
        controls_layout.addWidget(self.refresh_btn)
        
        controls_layout.addStretch()
        
        self.status_label = QLabel(f"GPUs detected: {self.device_count}")
        controls_layout.addWidget(self.status_label)
        
        layout.addLayout(controls_layout)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gpu_info)
        self.timer.start(2000)
        
        self.update_gpu_info()
    
    def format_bytes(self, bytes_value):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_value) < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def update_gpu_info(self):
        try:
            total_vram = 0
            used_vram = 0
            
            gpu_info_parts = []
            
            for i in range(self.device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                name = pynvml.nvmlDeviceGetName(handle)
                if name is None:
                    name = f"GPU {i}"
                
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_vram += memory_info.total
                used_vram += memory_info.used
                
                utilization = (memory_info.used / memory_info.total) * 100
                gpu_info_parts.append(
                    f"{name}: {utilization:.1f}% ({self.format_bytes(memory_info.used)} / {self.format_bytes(memory_info.total)})"
                )
            
            self.gpu_info_label.setText(" | ".join(gpu_info_parts))
            
            processes = []
            
            for i in range(self.device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                gpu_name = pynvml.nvmlDeviceGetName(handle)
                if gpu_name is None:
                    gpu_name = f"GPU {i}"
                
                for func_name, proc_func in [
                    ('Compute', pynvml.nvmlDeviceGetComputeRunningProcesses),
                    ('Graphics', pynvml.nvmlDeviceGetGraphicsRunningProcesses),
                ]:
                    try:
                        proc_info = proc_func(handle)
                        for proc in proc_info:
                            vram = 0
                            if hasattr(proc, 'usedGpuMemory') and proc.usedGpuMemory is not None:
                                vram = proc.usedGpuMemory
                            elif hasattr(proc, 'gpuUtil') and proc.gpuUtil is not None:
                                pass
                            if vram > 0:
                                existing = next((p for p in processes if p['pid'] == proc.pid), None)
                                if existing:
                                    existing['vram'] += vram
                                else:
                                    processes.append({
                                        'pid': proc.pid,
                                        'name': self._get_process_name(proc.pid),
                                        'vram': vram,
                                        'gpu': gpu_name
                                    })
                    except (pynvml.NVMLError, AttributeError):
                        pass
            
            processes.sort(key=lambda x: x['vram'], reverse=True)
            
            self.process_table.setRowCount(len(processes))
            
            for row, proc in enumerate(processes):
                self.process_table.setItem(row, 0, QTableWidgetItem(str(proc['pid'])))
                self.process_table.setItem(row, 1, QTableWidgetItem(proc['name']))
                self.process_table.setItem(row, 2, QTableWidgetItem(self.format_bytes(proc['vram'])))
                self.process_table.setItem(row, 3, QTableWidgetItem(proc['gpu']))
            
            self.status_label.setText(
                f"Total: {self.format_bytes(used_vram)} / {self.format_bytes(total_vram)} | Processes: {len(processes)}"
            )
            
        except pynvml.NVMLError as e:
            self.gpu_info_label.setText(f"NVML Error: {e}")
    
    def _get_process_name(self, pid):
        try:
            import psutil
            return psutil.Process(pid).name()
        except:
            return f"Process {pid}"
    
    def closeEvent(self, event):
        try:
            pynvml.nvmlShutdown()
        except:
            pass
        event.accept()


import os
import win32event
import win32api
import winerror


def main():
    mutex = win32event.CreateMutex(None, False, "GPU_VRAM_Monitor_SingleInstance")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        sys.exit(0)
    
    try:
        pynvml.nvmlInit()
    except pynvml.NVMLError as e:
        print(f"Failed to initialize NVML: {e}")
        print("Make sure NVIDIA drivers are installed and a CUDA-capable GPU is present.")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    app.setStyle("Fusion")
    
    window = GPUMonitorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
