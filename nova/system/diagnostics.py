"""
NOVA TV — System information and diagnostics.

Provides:
  • Network connectivity status.
  • CPU, memory, and temperature readings (on Raspberry Pi).
  • Uptime and storage information.
  • Platform detection (Pi vs. desktop).

Works cross-platform: returns safe stubs on Windows/macOS.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError

log = logging.getLogger(__name__)


@dataclass
class SystemInfo:
    """Snapshot of system state."""
    hostname: str = ""
    platform: str = ""
    is_raspberry_pi: bool = False
    pi_model: str = ""
    cpu_temp_c: float = 0.0
    cpu_usage_pct: float = 0.0
    mem_total_mb: float = 0.0
    mem_used_mb: float = 0.0
    mem_available_mb: float = 0.0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    uptime_seconds: float = 0.0
    ip_address: str = ""
    network_connected: bool = False
    network_ssid: str = ""
    python_version: str = ""
    nova_version: str = ""


def is_raspberry_pi() -> bool:
    """Detect if we're running on a Raspberry Pi."""
    if platform.system() != "Linux":
        return False
    try:
        with open("/proc/device-tree/model", "r") as f:
            model = f.read().lower()
            return "raspberry pi" in model
    except (OSError, IOError):
        pass
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "BCM" in line.upper():
                    return True
    except (OSError, IOError):
        pass
    return False


def get_pi_model() -> str:
    """Read the Pi model string."""
    try:
        with open("/proc/device-tree/model", "r") as f:
            return f.read().strip().rstrip("\x00")
    except (OSError, IOError):
        return ""


def get_cpu_temp() -> float:
    """Read CPU temperature in °C (Pi only)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except (OSError, IOError, ValueError):
        return 0.0


def get_memory_info() -> Tuple[float, float, float]:
    """Return (total_mb, used_mb, available_mb)."""
    if platform.system() == "Linux":
        try:
            with open("/proc/meminfo", "r") as f:
                info: Dict[str, int] = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        val = int(parts[1])  # kB
                        info[key] = val
                total = info.get("MemTotal", 0) / 1024
                available = info.get("MemAvailable", 0) / 1024
                used = total - available
                return (total, used, available)
        except (OSError, ValueError):
            pass
    # Fallback for Windows / unknown
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        total = stat.ullTotalPhys / (1024 * 1024)
        avail = stat.ullAvailPhys / (1024 * 1024)
        return (total, total - avail, avail)
    except Exception:
        return (0.0, 0.0, 0.0)


def get_disk_info(path: str = "/") -> Tuple[float, float]:
    """Return (total_gb, free_gb) for the given mount."""
    try:
        usage = shutil.disk_usage(path)
        return (usage.total / (1024**3), usage.free / (1024**3))
    except OSError:
        return (0.0, 0.0)


def get_ip_address() -> str:
    """Get the primary IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_uptime() -> float:
    """Return system uptime in seconds."""
    if platform.system() == "Linux":
        try:
            with open("/proc/uptime", "r") as f:
                return float(f.read().split()[0])
        except (OSError, ValueError):
            pass
    return 0.0


def get_wifi_ssid() -> str:
    """Get the connected Wi-Fi SSID (Linux only)."""
    try:
        result = subprocess.run(
            ["iwgetid", "-r"],
            capture_output=True, text=True, timeout=3,
        )
        return result.stdout.strip()
    except Exception:
        return ""


class NetworkChecker:
    """
    Background network connectivity checker.

    Pings a known URL periodically.  The UI reads ``connected``
    without blocking.
    """

    def __init__(self, check_url: str = "http://detectportal.firefox.com/success.txt",
                 interval: float = 30.0):
        self._url = check_url
        self._interval = interval
        self._connected = False
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="net-check")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def check_once(self) -> bool:
        try:
            resp = urlopen(self._url, timeout=5)
            self._connected = resp.status == 200
        except Exception:
            self._connected = False
        return self._connected

    def _worker(self) -> None:
        while self._running:
            self.check_once()
            time.sleep(self._interval)


def collect_system_info() -> SystemInfo:
    """Gather a full system-info snapshot."""
    from nova import __version__

    mem = get_memory_info()
    disk = get_disk_info("/" if platform.system() != "Windows" else "C:\\")

    return SystemInfo(
        hostname=socket.gethostname(),
        platform=f"{platform.system()} {platform.release()}",
        is_raspberry_pi=is_raspberry_pi(),
        pi_model=get_pi_model(),
        cpu_temp_c=get_cpu_temp(),
        mem_total_mb=mem[0],
        mem_used_mb=mem[1],
        mem_available_mb=mem[2],
        disk_total_gb=disk[0],
        disk_free_gb=disk[1],
        uptime_seconds=get_uptime(),
        ip_address=get_ip_address(),
        python_version=platform.python_version(),
        nova_version=__version__,
    )
