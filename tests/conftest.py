"""
NOVA TV — pytest configuration / shared fixtures.

Headless testing: forces the SDL dummy video driver so tests can construct
surfaces and the main loop without a real display.  Hardware-specific code is
stubbed where needed in individual tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the repo importable when running tests from anywhere
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force a headless SDL backend BEFORE pygame is imported anywhere
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _pygame_headless():
    """Initialise pygame once for the whole test session (dummy display)."""
    pygame.init()
    # A small display surface is needed by some font/surface APIs
    pygame.display.set_mode((640, 360))
    yield
    pygame.quit()


@pytest.fixture
def surface():
    """A fresh off-screen surface at the design resolution."""
    return pygame.Surface((1920, 1080))
