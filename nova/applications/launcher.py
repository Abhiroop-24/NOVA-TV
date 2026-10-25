"""
NOVA TV — Application launcher.

Manages external application entries defined in config/applications.json.
Each entry specifies a display name, icon, launch method, compatibility
status, and optional URL.

Launch methods:
  • "browser"  — open a URL in the system browser (e.g. chromium-browser).
  • "native"   — run an executable directly.
  • "internal" — handled inside NOVA TV (settings, media, etc.).
  • "unavailable" — shown but greyed out with a reason.

The launcher:
  1. Validates that the executable / browser exists before launching.
  2. Runs external processes asynchronously.
  3. Tracks the running process so NOVA TV can detect when it exits.
  4. Logs launch errors to ConfigManager.
  5. Never stores passwords.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


class LaunchMethod(Enum):
    BROWSER = "browser"
    NATIVE = "native"
    INTERNAL = "internal"
    UNAVAILABLE = "unavailable"


class CompatStatus(Enum):
    VERIFIED = "verified"             # tested and working
    EXPERIMENTAL = "experimental"     # browser fallback, not verified
    UNAVAILABLE = "unavailable"       # known not to work
    UNTESTED = "untested"             # not yet validated


@dataclass
class AppEntry:
    """A launchable application entry."""
    id: str
    name: str
    icon: str = ""
    description: str = ""
    launch_method: LaunchMethod = LaunchMethod.UNAVAILABLE
    url: str = ""
    executable: str = ""
    args: List[str] = field(default_factory=list)
    compat_status: CompatStatus = CompatStatus.UNTESTED
    compat_notes: str = ""
    category: str = "app"
    last_error: str = ""
    is_pinned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "launch_method": self.launch_method.value,
            "url": self.url,
            "executable": self.executable,
            "args": self.args,
            "compat_status": self.compat_status.value,
            "compat_notes": self.compat_notes,
            "category": self.category,
            "is_pinned": self.is_pinned,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AppEntry:
        return cls(
            id=d.get("id", "unknown"),
            name=d.get("name", "Unknown"),
            icon=d.get("icon", ""),
            description=d.get("description", ""),
            launch_method=LaunchMethod(d.get("launch_method", "unavailable")),
            url=d.get("url", ""),
            executable=d.get("executable", ""),
            args=d.get("args", []),
            compat_status=CompatStatus(d.get("compat_status", "untested")),
            compat_notes=d.get("compat_notes", ""),
            category=d.get("category", "app"),
            is_pinned=d.get("is_pinned", False),
        )


class AppLauncher:
    """
    Manages application entries and launches external processes.

    Tracks the active external process so the UI can detect when to
    re-display NOVA TV.
    """

    def __init__(self, apps_config_path: str, error_callback: Optional[Callable[[str, str], None]] = None):
        self._config_path = apps_config_path
        self._entries: Dict[str, AppEntry] = {}
        self._active_proc: Optional[subprocess.Popen] = None
        self._active_app_id: Optional[str] = None
        self._error_cb = error_callback
        self._browser_cmd: Optional[str] = None

    # ── Load / save ─────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load application entries from JSON config."""
        if not os.path.isfile(self._config_path):
            log.warning("Apps config not found: %s", self._config_path)
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            apps_list = data if isinstance(data, list) else data.get("applications", [])
            self._entries.clear()
            for entry_data in apps_list:
                entry = AppEntry.from_dict(entry_data)
                self._entries[entry.id] = entry
            log.info("Loaded %d application entries", len(self._entries))
        except (json.JSONDecodeError, OSError) as exc:
            log.error("Failed to load apps config: %s", exc)

    @property
    def entries(self) -> List[AppEntry]:
        return list(self._entries.values())

    def get(self, app_id: str) -> Optional[AppEntry]:
        return self._entries.get(app_id)

    # ── Browser detection ───────────────────────────────────────────────────

    def _find_browser(self) -> Optional[str]:
        """Detect an installed browser."""
        if self._browser_cmd:
            return self._browser_cmd

        candidates = []
        if platform.system() == "Windows":
            candidates = ["start", "chrome", "msedge", "firefox"]
        else:
            candidates = [
                "chromium",          # Raspberry Pi OS
                "chromium-browser",  # Ubuntu/older Pi
                "firefox-esr",
                "firefox",
                "surf",
                "midori",
            ]

        for cmd in candidates:
            if shutil.which(cmd):
                self._browser_cmd = cmd
                log.info("Detected browser: %s", cmd)
                return cmd

        log.warning("No browser found on this system")
        return None

    # ── Launch ──────────────────────────────────────────────────────────────

    def launch(self, app_id: str) -> bool:
        """
        Launch an application by ID.

        Returns True if the launch was initiated, False on failure.
        """
        entry = self._entries.get(app_id)
        if not entry:
            self._report_error(app_id, f"Unknown application: {app_id}")
            return False

        if entry.launch_method == LaunchMethod.UNAVAILABLE:
            reason = entry.compat_notes or "This application is not available on this device."
            self._report_error(app_id, reason)
            return False

        if entry.launch_method == LaunchMethod.INTERNAL:
            # Internal navigation — handled by the UI, not here
            log.info("Internal action: %s", app_id)
            return True

        if entry.launch_method == LaunchMethod.BROWSER:
            return self._launch_browser(entry)

        if entry.launch_method == LaunchMethod.NATIVE:
            return self._launch_native(entry)

        return False

    def _launch_browser(self, entry: AppEntry) -> bool:
        """Open a URL in the external browser."""
        if not entry.url:
            self._report_error(entry.id, "No URL configured")
            return False

        browser = self._find_browser()
        if not browser:
            self._report_error(entry.id, "No browser installed. Install chromium-browser.")
            return False

        try:
            if platform.system() == "Windows":
                # On Windows, use 'start' via shell
                cmd = ["cmd", "/c", "start", "", entry.url]
                self._active_proc = subprocess.Popen(cmd, shell=False)
            else:
                # Kiosk mode for a clean TV experience
                cmd = [browser]
                if browser in ("chromium-browser", "chromium"):
                    cmd += [
                        "--kiosk",
                        "--noerrdialogs",
                        "--disable-infobars",
                        "--no-first-run",
                        "--disable-translate",
                        "--disable-features=TranslateUI",
                        "--check-for-update-interval=31536000",
                    ]
                cmd.append(entry.url)
                env = os.environ.copy()
                env["DISPLAY"] = ":0"
                self._active_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
            self._active_app_id = entry.id
            log.info("Launched browser for %s: %s", entry.name, entry.url)
            return True
        except Exception as exc:
            self._report_error(entry.id, f"Browser launch failed: {exc}")
            return False

    def _launch_native(self, entry: AppEntry) -> bool:
        """Launch a native executable."""
        exe = entry.executable
        if not exe:
            self._report_error(entry.id, "No executable configured")
            return False

        if not shutil.which(exe) and not os.path.isfile(exe):
            self._report_error(entry.id, f"Executable not found: {exe}")
            return False

        try:
            cmd = [exe] + entry.args
            self._active_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._active_app_id = entry.id
            log.info("Launched native app %s: %s", entry.name, cmd)
            return True
        except Exception as exc:
            self._report_error(entry.id, f"Launch failed: {exc}")
            return False

    # ── Active process tracking ─────────────────────────────────────────────

    @property
    def is_app_running(self) -> bool:
        """True if an external app is currently running."""
        if self._active_proc is None:
            return False
        if self._active_proc.poll() is not None:
            log.info("External app %s exited (code %d)",
                     self._active_app_id, self._active_proc.returncode)
            self._active_proc = None
            self._active_app_id = None
            return False
        return True

    @property
    def active_app_id(self) -> Optional[str]:
        if self.is_app_running:
            return self._active_app_id
        return None

    def kill_active(self) -> None:
        """Forcefully terminate the active external app."""
        if self._active_proc and self._active_proc.poll() is None:
            self._active_proc.terminate()
            try:
                self._active_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._active_proc.kill()
            log.info("Killed active app %s", self._active_app_id)
        self._active_proc = None
        self._active_app_id = None

    # ── Error reporting ─────────────────────────────────────────────────────

    def _report_error(self, app_id: str, message: str) -> None:
        log.error("App %s: %s", app_id, message)
        entry = self._entries.get(app_id)
        if entry:
            entry.last_error = message
        if self._error_cb:
            self._error_cb(app_id, message)

    # ── Compatibility report ────────────────────────────────────────────────

    def compatibility_report(self) -> List[Dict[str, str]]:
        """Return a list of dicts for the service-compatibility page."""
        report = []
        for entry in self._entries.values():
            report.append({
                "name": entry.name,
                "method": entry.launch_method.value,
                "status": entry.compat_status.value,
                "notes": entry.compat_notes,
                "last_error": entry.last_error,
            })
        return report
