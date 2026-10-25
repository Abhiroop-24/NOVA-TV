"""
NOVA TV — Configuration persistence tests.

Covers atomic writes, corruption recovery, favourites, and the error log.
These are pure-Python and need no display, but run under the headless conftest
anyway.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from nova.settings.config import ConfigManager, DEFAULT_SETTINGS


def test_load_creates_defaults(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    # Settings absent on disk → defaults are used
    assert cfg.get("display.resolution") == [1920, 1080]
    assert cfg.get("display.fullscreen") is True
    assert cfg.favourites == []
    assert cfg.recent_errors == []


def test_set_and_save_roundtrip(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    cfg.set("display.fullscreen", False)
    cfg.set("media.player_command", "vlc")
    cfg.add_favourite("youtube")
    cfg.save()

    # Re-load from a fresh instance → values persisted
    cfg2 = ConfigManager(config_dir=str(tmp_path))
    cfg2.load()
    assert cfg2.get("display.fullscreen") is False
    assert cfg2.get("media.player_command") == "vlc"
    assert cfg2.favourites == ["youtube"]


def test_atomic_write_leaves_no_tmp(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    cfg.save()
    # No leftover .tmp files
    assert not list(Path(tmp_path).glob("*.tmp"))
    assert (tmp_path / "settings.json").is_file()


def test_corrupt_config_restores_defaults(tmp_path):
    # Write a broken settings file
    (tmp_path / "settings.json").write_text("{not valid json", encoding="utf-8")
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    # Defaults restored
    assert cfg.get("display.fps_target") == 30
    # Corrupt file backed up
    assert (tmp_path / "settings.json.corrupt").is_file()


def test_deep_merge_keeps_user_overrides(tmp_path):
    # Partial user file: only overrides one key
    (tmp_path / "settings.json").write_text(
        json.dumps({"display": {"fullscreen": False}}), encoding="utf-8"
    )
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    assert cfg.get("display.fullscreen") is False   # overridden
    assert cfg.get("display.resolution") == [1920, 1080]  # default kept
    assert cfg.get("media.player_command") == "mpv"  # other section intact


def test_favourites_toggle(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    assert cfg.toggle_favourite("youtube") is True
    assert cfg.is_favourite("youtube")
    assert cfg.toggle_favourite("youtube") is False
    assert not cfg.is_favourite("youtube")


def test_error_log_capped(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    for i in range(60):
        cfg.log_error("test", f"err {i}")
    assert len(cfg.recent_errors) == 50
    # Newest errors kept
    assert cfg.recent_errors[-1]["message"] == "err 59"
    cfg.clear_errors()
    assert cfg.recent_errors == []


def test_factory_reset(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    cfg.add_favourite("youtube")
    cfg.save()
    cfg.factory_reset()
    cfg2 = ConfigManager(config_dir=str(tmp_path))
    cfg2.load()
    assert cfg2.favourites == []
    assert not (tmp_path / "settings.json").is_file()


def test_dot_path_get_returns_default(tmp_path):
    cfg = ConfigManager(config_dir=str(tmp_path))
    cfg.load()
    assert cfg.get("does.not.exist", "fallback") == "fallback"
