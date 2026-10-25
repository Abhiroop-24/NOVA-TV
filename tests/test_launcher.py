"""
NOVA TV — Application launcher tests.

Covers entry loading from JSON, missing-executable rejection, unavailable
status, and the compatibility report.  No real processes are spawned; we
patch subprocess.Popen where needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from nova.applications.launcher import AppLauncher, AppEntry, LaunchMethod, CompatStatus


def write_apps(tmp_path, apps):
    p = tmp_path / "applications.json"
    p.write_text(json.dumps({"applications": apps}), encoding="utf-8")
    return str(p)


def test_loads_entries(tmp_path):
    path = write_apps(tmp_path, [
        {"id": "a", "name": "Alpha", "launch_method": "internal",
         "compat_status": "verified"},
        {"id": "b", "name": "Beta", "launch_method": "browser",
         "url": "https://example.com", "compat_status": "experimental"},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    assert len(launcher.entries) == 2
    assert launcher.get("a").launch_method == LaunchMethod.INTERNAL
    assert launcher.get("b").url == "https://example.com"


def test_missing_config_is_empty(tmp_path):
    launcher = AppLauncher(str(tmp_path / "nope.json"))
    launcher.load()  # should not raise
    assert launcher.entries == []


def test_unavailable_rejects_launch(tmp_path):
    path = write_apps(tmp_path, [
        {"id": "x", "name": "X", "launch_method": "unavailable",
         "compat_status": "unavailable",
         "compat_notes": "Not supported on this device."},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    ok = launcher.launch("x")
    assert ok is False
    assert launcher.get("x").last_error != ""


def test_native_missing_executable_reports_error(tmp_path):
    path = write_apps(tmp_path, [
        {"id": "n", "name": "Native", "launch_method": "native",
         "executable": "this_binary_does_not_exist_xyz", "compat_status": "untested"},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    assert launcher.launch("n") is False
    assert "not found" in launcher.get("n").last_error.lower()


def test_browser_launch_without_browser_or_url(tmp_path, monkeypatch):
    path = write_apps(tmp_path, [
        {"id": "w", "name": "Web", "launch_method": "browser",
         "url": "", "compat_status": "experimental"},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    # No URL → fails
    assert launcher.launch("w") is False
    assert "no url" in launcher.get("w").last_error.lower()


def test_unknown_app_returns_false(tmp_path):
    path = write_apps(tmp_path, [])
    launcher = AppLauncher(path)
    launcher.load()
    assert launcher.launch("nope") is False


def test_internal_returns_true_without_spawning(tmp_path):
    path = write_apps(tmp_path, [
        {"id": "s", "name": "Settings", "launch_method": "internal",
         "compat_status": "verified"},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    assert launcher.launch("s") is True
    # No external process should be tracked
    assert launcher.is_app_running is False


def test_compat_report_fields(tmp_path):
    path = write_apps(tmp_path, [
        {"id": "y", "name": "YouTube", "launch_method": "browser",
         "url": "https://youtube.com", "compat_status": "experimental",
         "compat_notes": "Limited on Pi"},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    report = {r["name"]: r for r in launcher.compatibility_report()}
    row = report["YouTube"]
    assert set(row.keys()) == {"name", "method", "status", "notes", "last_error"}
    assert row["method"] == "browser"
    assert row["status"] == "experimental"
    assert row["notes"] == "Limited on Pi"


def test_browser_launch_patches_subprocess(tmp_path, monkeypatch):
    path = write_apps(tmp_path, [
        {"id": "yt", "name": "YouTube", "launch_method": "browser",
         "url": "https://example.com", "compat_status": "experimental"},
    ])
    launcher = AppLauncher(path)
    launcher.load()
    # Force a browser to be "found"
    monkeypatch.setattr(launcher, "_find_browser", lambda: "chromium-browser")
    with mock.patch("subprocess.Popen") as popen:
        popen.return_value.poll.return_value = None
        assert launcher.launch("yt") is True
        popen.assert_called_once()
        # Process tracked
        assert launcher.is_app_running is True
    launcher.kill_active()
