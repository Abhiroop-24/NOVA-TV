"""
NOVA TV — System diagnostics + resource-bounds tests.

Verifies graceful offline/low-memory behaviour: the network checker handles
unreachable URLs without raising, the image cache is bounded, and system
info collection returns safe stubs off the Pi.
"""

from __future__ import annotations

import os
from unittest import mock

from nova.assets import _IMAGE_CACHE_MAX, _load_image_cached, clear_caches
from nova.system import diagnostics as diag


def test_network_checker_offline_is_safe():
    # An unreachable URL must not raise; it simply reports disconnected.
    nc = diag.NetworkChecker(check_url="http://127.0.0.1:9/no-such", interval=999)
    with mock.patch("nova.system.diagnostics.urlopen", side_effect=Exception("offline")):
        assert nc.check_once() is False
    assert nc.connected is False
    nc.stop()


def test_image_cache_is_bounded():
    # The cache decorator must report its declared bound.
    info = _load_image_cached.cache_info()
    assert info.maxsize == _IMAGE_CACHE_MAX


def test_clear_caches_resets():
    clear_caches()
    info = _load_image_cached.cache_info()
    assert info.currsize == 0


def test_system_info_stubs_off_pi():
    info = diag.collect_system_info()
    # Platform string should be populated even off the Pi
    assert info.platform != ""
    assert info.python_version != ""
    assert info.nova_version != ""
    # On a non-Pi dev machine, is_raspberry_pi is False
    assert isinstance(info.is_raspberry_pi, bool)


def test_is_raspberry_pi_returns_bool():
    assert isinstance(diag.is_raspberry_pi(), bool)


def test_ip_address_safe():
    ip = diag.get_ip_address()
    # Should always return a string; on an isolated machine it may be 127.0.0.1
    assert isinstance(ip, str)
    assert len(ip) > 0
