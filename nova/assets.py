"""
NOVA TV — Asset manager.

Handles locating and loading images, icons, and fonts from the assets/
directory.  Provides a bounded LRU cache for scaled images so we never
hold more than ~50 surfaces in memory.
"""

from __future__ import annotations

import os
import functools
import logging
from typing import Optional, Tuple

import pygame

from nova import theme

log = logging.getLogger(__name__)

# ── Path helpers ─────────────────────────────────────────────────────────────

_PROJECT_ROOT: Optional[str] = None


def _find_project_root() -> str:
    """Walk up from this file to find the directory containing 'assets/'."""
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        if os.path.isdir(os.path.join(d, "assets")):
            return d
        d = os.path.dirname(d)
    # Fallback: assume sibling of nova/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_root() -> str:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = _find_project_root()
    return _PROJECT_ROOT


def assets_dir() -> str:
    return os.path.join(project_root(), "assets")


def icons_dir() -> str:
    return os.path.join(assets_dir(), "icons")


def artwork_dir() -> str:
    return os.path.join(assets_dir(), "artwork")


def fonts_dir() -> str:
    return os.path.join(assets_dir(), "fonts")


# ── Font loading ─────────────────────────────────────────────────────────────

_font_cache: dict[Tuple[str, int], pygame.font.Font] = {}

# Preferred font filename inside assets/fonts/
_PREFERRED_FONT = "Inter-Regular.ttf"
_PREFERRED_FONT_BOLD = "Inter-Bold.ttf"


def _resolve_font_path(bold: bool = False) -> Optional[str]:
    """Return the path to the bundled font, or None if not found."""
    name = _PREFERRED_FONT_BOLD if bold else _PREFERRED_FONT
    path = os.path.join(fonts_dir(), name)
    if os.path.isfile(path):
        return path
    # Try any .ttf in the fonts dir
    fd = fonts_dir()
    if os.path.isdir(fd):
        for f in sorted(os.listdir(fd)):
            if f.lower().endswith(".ttf"):
                return os.path.join(fd, f)
    return None


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Get a cached Pygame font at the given pixel size."""
    key = ("bold" if bold else "regular", size)
    if key not in _font_cache:
        path = _resolve_font_path(bold)
        if path:
            try:
                _font_cache[key] = pygame.font.Font(path, size)
            except Exception:
                log.warning("Failed to load font %s, using default", path)
                _font_cache[key] = pygame.font.SysFont("sans", size, bold=bold)
        else:
            _font_cache[key] = pygame.font.SysFont("sans", size, bold=bold)
    return _font_cache[key]


# ── Image loading with bounded cache ────────────────────────────────────────

_IMAGE_CACHE_MAX = 80


@functools.lru_cache(maxsize=_IMAGE_CACHE_MAX)
def _load_image_cached(path: str, width: int, height: int) -> Optional[pygame.Surface]:
    """Load and scale an image.  Returns None on failure."""
    try:
        surf = pygame.image.load(path)
        if width > 0 and height > 0:
            surf = pygame.transform.smoothscale(surf, (width, height))
        return surf.convert_alpha()
    except Exception as exc:
        log.debug("Cannot load image %s: %s", path, exc)
        return None


def load_image(path: str, size: Optional[Tuple[int, int]] = None) -> Optional[pygame.Surface]:
    """Public API: load an image, optionally scaling to (w, h)."""
    if not os.path.isfile(path):
        return None
    w, h = size if size else (0, 0)
    return _load_image_cached(path, w, h)


def load_icon(name: str, size: Tuple[int, int] = (32, 32)) -> Optional[pygame.Surface]:
    """Load a named icon from the icons directory."""
    filename = theme.ICON_MAP.get(name, f"{name}.png")
    path = os.path.join(icons_dir(), filename)
    return load_image(path, size)


def load_artwork(filename: str, size: Optional[Tuple[int, int]] = None) -> Optional[pygame.Surface]:
    """Load artwork from the artwork directory."""
    path = os.path.join(artwork_dir(), filename)
    return load_image(path, size)


# ── Placeholder generation ──────────────────────────────────────────────────

def make_placeholder(
    width: int,
    height: int,
    color: Tuple[int, int, int] = theme.BG_ELEVATED,
    label: str = "",
) -> pygame.Surface:
    """Generate a coloured placeholder surface with optional centred label."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(color)
    if label:
        font = get_font(theme.FONT_SIZE_CAPTION)
        text = font.render(label, True, theme.TEXT_SECONDARY)
        tx = (width - text.get_width()) // 2
        ty = (height - text.get_height()) // 2
        surf.blit(text, (tx, ty))
    return surf


# ── Cleanup ──────────────────────────────────────────────────────────────────

def clear_caches() -> None:
    """Free all cached surfaces and fonts (for shutdown or theme change)."""
    _load_image_cached.cache_clear()
    _font_cache.clear()
