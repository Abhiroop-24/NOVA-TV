"""
NOVA TV — Installation artifact validation.

Validates that the deployment artifacts are well-formed:
- Shell scripts pass `bash -n` (syntax check) when bash is available.
- systemd unit files parse as systemd-style INI with the required sections.
- applications.json is valid JSON with the required per-entry fields.

Skips shell checks when bash is not present (e.g. on a Windows dev machine).
"""

from __future__ import annotations

import configparser
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SYSTEMD = ROOT / "systemd"
CONFIG = ROOT / "config"

SHELL_SCRIPTS = ["install.sh", "uninstall.sh", "run-dev.sh", "diagnostics.sh"]


def _has_bash() -> bool:
    return shutil.which("bash") is not None


@pytest.mark.skipif(not _has_bash(), reason="bash not available on this platform")
@pytest.mark.parametrize("script", SHELL_SCRIPTS)
def test_shell_script_syntax(script):
    path = SCRIPTS / script
    assert path.is_file(), f"{script} missing"
    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    assert result.returncode == 0, f"{script} syntax error:\n{result.stderr}"


def test_shell_scripts_have_shebang():
    for script in SHELL_SCRIPTS:
        path = SCRIPTS / script
        assert path.is_file()
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("#!"), f"{script} missing shebang"


def test_service_unit_sections():
    unit = SYSTEMD / "nova-tv.service"
    assert unit.is_file()
    parser = configparser.ConfigParser(strict=False)
    # systemd allows repeated/no-value keys; relax configparser
    parser.optionxform = str
    parser.read(unit)
    assert parser.has_section("Unit")
    assert parser.has_section("Service")
    assert parser.has_section("Install")
    assert parser.has_option("Service", "ExecStart")
    assert parser.has_option("Service", "Restart")
    assert parser.get("Service", "Restart") == "on-failure"


def test_target_unit_parses():
    target = SYSTEMD / "nova-tv.target"
    assert target.is_file()
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str
    parser.read(target)
    assert parser.has_section("Unit")


def test_applications_json_valid():
    p = CONFIG / "applications.json"
    assert p.is_file()
    data = json.loads(p.read_text(encoding="utf-8"))
    apps = data.get("applications", [])
    assert isinstance(apps, list) and len(apps) > 0
    required = {"id", "name", "launch_method", "compat_status"}
    for entry in apps:
        missing = required - set(entry.keys())
        assert not missing, f"entry {entry.get('id')} missing {missing}"
        assert entry["launch_method"] in {"internal", "browser", "native", "unavailable"}
        assert entry["compat_status"] in {"verified", "experimental", "unavailable", "untested"}
