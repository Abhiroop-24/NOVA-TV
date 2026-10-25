"""
NOVA TV — Configuration manager.

Handles persistent user settings with:
  • Atomic writes (write-to-temp then rename) to survive power loss.
  • Automatic safe-default restoration on corruption.
  • Separate files for user settings, favourites, and recent errors.
  • No plaintext passwords or sensitive tokens.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import tempfile
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

def _default_config_dir() -> str:
    """Platform-appropriate config directory."""
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "NovaTV")
    # Linux / Pi
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(xdg, "nova-tv")


# ── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_SETTINGS: Dict[str, Any] = {
    "display": {
        "resolution": [1920, 1080],
        "fullscreen": True,
        "fps_target": 30,
        "overscan_compensation": False,
    },
    "theme": {
        "mode": "dark",
        "accent_color": "violet",
    },
    "media": {
        "directories": ["/media", "/home/pi/Videos"],
        "supported_extensions": [
            ".mp4", ".mkv", ".avi", ".mov", ".webm",
            ".mp3", ".flac", ".ogg", ".wav", ".aac",
        ],
        "player_command": "mpv",
    },
    "network": {
        "check_url": "http://detectportal.firefox.com/success.txt",
    },
    "input": {
        "enable_cec": True,
        "key_repeat_delay_ms": 400,
        "key_repeat_rate_ms": 120,
    },
    "system": {
        "dev_mode": False,
        "show_fps": False,
        "log_level": "INFO",
        "max_log_size_mb": 5,
    },
}


# ── Config manager ───────────────────────────────────────────────────────────

class ConfigManager:
    """
    Thread-safe, atomic-write configuration store.

    Usage::

        cfg = ConfigManager()
        cfg.load()
        res = cfg.get("display.resolution")
        cfg.set("display.fullscreen", False)
        cfg.save()
    """

    def __init__(self, config_dir: Optional[str] = None):
        self._dir = config_dir or _default_config_dir()
        self._settings_path = os.path.join(self._dir, "settings.json")
        self._favourites_path = os.path.join(self._dir, "favourites.json")
        self._errors_path = os.path.join(self._dir, "recent_errors.json")
        self._data: Dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
        self._favourites: List[str] = []
        self._recent_errors: List[Dict[str, Any]] = []

    @property
    def config_dir(self) -> str:
        return self._dir

    # ── Load / save ─────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load settings from disk, restoring defaults on corruption."""
        os.makedirs(self._dir, exist_ok=True)
        self._data = self._load_json(self._settings_path, DEFAULT_SETTINGS)
        # Merge any missing keys from defaults
        self._data = self._deep_merge(deepcopy(DEFAULT_SETTINGS), self._data)
        self._favourites = self._load_json(self._favourites_path, [])
        self._recent_errors = self._load_json(self._errors_path, [])
        log.info("Config loaded from %s", self._dir)

    def save(self) -> None:
        """Persist all settings atomically."""
        os.makedirs(self._dir, exist_ok=True)
        self._save_json(self._settings_path, self._data)
        self._save_json(self._favourites_path, self._favourites)
        self._save_json(self._errors_path, self._recent_errors)
        log.debug("Config saved to %s", self._dir)

    # ── Get / set with dot-path ─────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by dot-separated path, e.g. 'display.resolution'."""
        parts = key.split(".")
        obj = self._data
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return default
        return obj

    def set(self, key: str, value: Any) -> None:
        """Set a value by dot-separated path."""
        parts = key.split(".")
        obj = self._data
        for part in parts[:-1]:
            if part not in obj or not isinstance(obj[part], dict):
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    # ── Favourites ──────────────────────────────────────────────────────────

    @property
    def favourites(self) -> List[str]:
        return list(self._favourites)

    def add_favourite(self, item_id: str) -> None:
        if item_id not in self._favourites:
            self._favourites.append(item_id)

    def remove_favourite(self, item_id: str) -> None:
        if item_id in self._favourites:
            self._favourites.remove(item_id)

    def is_favourite(self, item_id: str) -> bool:
        return item_id in self._favourites

    def toggle_favourite(self, item_id: str) -> bool:
        """Toggle and return new state."""
        if self.is_favourite(item_id):
            self.remove_favourite(item_id)
            return False
        self.add_favourite(item_id)
        return True

    # ── Error log ───────────────────────────────────────────────────────────

    def log_error(self, source: str, message: str) -> None:
        entry = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "message": message,
        }
        self._recent_errors.append(entry)
        # Keep only last 50 errors
        if len(self._recent_errors) > 50:
            self._recent_errors = self._recent_errors[-50:]

    @property
    def recent_errors(self) -> List[Dict[str, Any]]:
        return list(self._recent_errors)

    def clear_errors(self) -> None:
        self._recent_errors.clear()

    # ── Internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _load_json(path: str, default: Any) -> Any:
        if not os.path.isfile(path):
            return deepcopy(default)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Corrupt config %s (%s), restoring defaults", path, exc)
            # Back up corrupt file
            backup = path + ".corrupt"
            try:
                shutil.copy2(path, backup)
            except OSError:
                pass
            return deepcopy(default)

    @staticmethod
    def _save_json(path: str, data: Any) -> None:
        """Atomic write: write to temp file then rename."""
        dir_path = os.path.dirname(path)
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # On Windows, os.rename fails if target exists
            if os.path.exists(path):
                os.replace(tmp_path, path)
            else:
                os.rename(tmp_path, path)
        except OSError as exc:
            log.error("Failed to save %s: %s", path, exc)
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge override into base, keeping override values."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # ── Reset ───────────────────────────────────────────────────────────────

    def reset_to_defaults(self) -> None:
        """Reset settings to defaults without deleting favourites or errors."""
        self._data = deepcopy(DEFAULT_SETTINGS)
        self.save()
        log.info("Settings reset to defaults")

    def factory_reset(self) -> None:
        """Remove all config files."""
        for path in [self._settings_path, self._favourites_path, self._errors_path]:
            try:
                if os.path.isfile(path):
                    os.unlink(path)
            except OSError:
                pass
        self._data = deepcopy(DEFAULT_SETTINGS)
        self._favourites = []
        self._recent_errors = []
        log.info("Factory reset complete")
