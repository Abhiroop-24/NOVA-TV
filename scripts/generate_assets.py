#!/usr/bin/env python3
"""
NOVA TV — Procedural asset generator.

Generates licence-free, geometric PNG icons and artwork into the assets/
directories so the project has bundled, good-looking assets out of the box.

Usage (run from the repository root, with the project's venv active):

    python scripts/generate_assets.py icons      # draw all theme.ICON_MAP icons
    python scripts/generate_assets.py artwork    # draw hero + demo posters
    python scripts/generate_assets.py all        # both

No external image files are required.  Everything is drawn with pygame.draw.
Replace any generated file with your own licensed artwork; the filenames must
match what the code expects (see nova/theme.py ICON_MAP and home_screen.py).
"""

from __future__ import annotations

import os
import sys

import pygame

# Make `nova` importable when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nova import theme  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(ROOT, "assets", "icons")
ARTWORK_DIR = os.path.join(ROOT, "assets", "artwork")

ICON_SIZE = 128
ACCENT = theme.ACCENT_PRIMARY
SECONDARY = theme.TEXT_SECONDARY
SURFACE = theme.BG_ELEVATED


# ── Drawing helpers ──────────────────────────────────────────────────────────

def _new_icon() -> pygame.Surface:
    surf = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


def _glyph_home() -> pygame.Surface:
    s = _new_icon()
    cx = ICON_SIZE // 2
    # Roof
    pygame.draw.polygon(s, ACCENT,
                        [(cx, 22), (28, 64), (100, 64)])
    # Body
    pygame.draw.rect(s, ACCENT, (cx - 28, 64, 56, 40), border_radius=4)
    # Door
    pygame.draw.rect(s, SURFACE, (cx - 8, 74, 16, 30), border_radius=2)
    return s


def _glyph_apps() -> pygame.Surface:
    s = _new_icon()
    for r in range(3):
        for c in range(3):
            x = 22 + c * 30
            y = 22 + r * 30
            pygame.draw.rect(s, ACCENT, (x, y, 24, 24), border_radius=5)
    return s


def _glyph_movies() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.rect(s, ACCENT, (24, 32, 80, 64), border_radius=6)
    pygame.draw.rect(s, SURFACE, (24, 32, 80, 64), 3, border_radius=6)
    # Play triangle
    pygame.draw.polygon(s, SECONDARY,
                        [(48, 48), (48, 80), (80, 64)])
    return s


def _glyph_favourites() -> pygame.Surface:
    s = _new_icon()
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2 + 4
    pygame.draw.polygon(s, ACCENT,
                        [(cx, cy + 28), (cx - 34, cy - 6), (cx - 14, cy - 26),
                         (cx, cy - 12), (cx + 14, cy - 26), (cx + 34, cy - 6)])
    return s


def _glyph_settings() -> pygame.Surface:
    s = _new_icon()
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    # Outer ring with teeth
    for i in range(8):
        ang = i * 45
        import math
        a = math.radians(ang)
        x1 = cx + int(40 * math.cos(a))
        y1 = cy + int(40 * math.sin(a))
        x2 = cx + int(50 * math.cos(a))
        y2 = cy + int(50 * math.sin(a))
        pygame.draw.line(s, ACCENT, (x1, y1), (x2, y2), 8)
    pygame.draw.circle(s, ACCENT, (cx, cy), 36, 0)
    pygame.draw.circle(s, SURFACE, (cx, cy), 18, 0)
    return s


def _glyph_search() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.circle(s, ACCENT, (52, 52), 24, 6)
    pygame.draw.line(s, ACCENT, (70, 70), (98, 98), 8)
    return s


def _glyph_play() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.polygon(s, ACCENT,
                        [(44, 32), (44, 96), (96, 64)])
    return s


def _glyph_back() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.polygon(s, ACCENT,
                        [(78, 32), (44, 64), (78, 96)])
    pygame.draw.rect(s, ACCENT, (44, 56, 48, 16))
    return s


def _glyph_info() -> pygame.Surface:
    s = _new_icon()
    cx = ICON_SIZE // 2
    pygame.draw.circle(s, ACCENT, (cx, cx), 44, 6)
    pygame.draw.circle(s, ACCENT, (cx, 38), 6)
    pygame.draw.rect(s, ACCENT, (cx - 6, 54, 12, 34), border_radius=3)
    return s


def _glyph_error() -> pygame.Surface:
    s = _new_icon()
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    pygame.draw.polygon(s, theme.STATUS_ERROR,
                        [(cx, 22), (104, 100), (24, 100)])
    pygame.draw.line(s, SURFACE, (cx, 48), (cx, 78), 8)
    pygame.draw.circle(s, SURFACE, (cx, 88), 5)
    return s


def _glyph_check() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.line(s, theme.STATUS_OK, (30, 66), (52, 88), 10)
    pygame.draw.line(s, theme.STATUS_OK, (52, 88), (100, 38), 10)
    return s


def _glyph_dot(name: str, color) -> pygame.Surface:
    s = _new_icon()
    pygame.draw.circle(s, color, (ICON_SIZE // 2, ICON_SIZE // 2), 36)
    pygame.draw.circle(s, SURFACE, (ICON_SIZE // 2, ICON_SIZE // 2), 36, 0)
    # simple concentric
    pygame.draw.circle(s, color, (ICON_SIZE // 2, ICON_SIZE // 2), 28)
    pygame.draw.circle(s, SURFACE, (ICON_SIZE // 2, ICON_SIZE // 2), 18)
    pygame.draw.circle(s, color, (ICON_SIZE // 2, ICON_SIZE // 2), 10)
    return s


def _glyph_folder() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.rect(s, ACCENT, (24, 36, 80, 64), border_radius=6)
    pygame.draw.rect(s, SURFACE, (24, 36, 80, 18), border_radius=6)
    pygame.draw.rect(s, ACCENT, (24, 54, 80, 46), border_radius=6)
    pygame.draw.rect(s, theme.BG_ELEVATED, (24, 36, 80, 64), 3, border_radius=6)
    return s


def _glyph_file_video() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.rect(s, ACCENT, (34, 26, 60, 76), border_radius=4)
    pygame.draw.polygon(s, SURFACE,
                        [(48, 50), (48, 78), (80, 64)])
    return s


def _glyph_file_audio() -> pygame.Surface:
    s = _new_icon()
    cx, cy = 64, 64
    pygame.draw.circle(s, theme.ACCENT_SECONDARY, (cx, cy + 10), 12)
    pygame.draw.line(s, theme.ACCENT_SECONDARY, (cx + 12, cy + 10), (cx + 12, cy - 18), 5)
    return s


def _glyph_generic() -> pygame.Surface:
    s = _new_icon()
    pygame.draw.circle(s, ACCENT, (ICON_SIZE // 2, ICON_SIZE // 2), 40, 5)
    return s


GLYPHS = {
    "home": _glyph_home,
    "apps": _glyph_apps,
    "movies": _glyph_movies,
    "favourites": _glyph_favourites,
    "settings": _glyph_settings,
    "network": _glyph_generic,
    "search": _glyph_search,
    "play": _glyph_play,
    "back": _glyph_back,
    "info": _glyph_info,
    "error": _glyph_error,
    "check": _glyph_check,
    "wifi": lambda: _glyph_dot("wifi", theme.ACCENT_SECONDARY),
    "ethernet": lambda: _glyph_dot("ethernet", theme.STATUS_OK),
    "bluetooth": lambda: _glyph_dot("bluetooth", theme.ACCENT_SECONDARY),
    "usb": _glyph_generic,
    "folder": _glyph_folder,
    "file_video": _glyph_file_video,
    "file_audio": _glyph_file_audio,
    "cec": _glyph_generic,
    "diagnostic": _glyph_info,
    "about": _glyph_info,
    "clock": _glyph_generic,
}


def generate_icons() -> int:
    os.makedirs(ICONS_DIR, exist_ok=True)
    count = 0
    for name, filename in theme.ICON_MAP.items():
        glyph_fn = GLYPHS.get(name, _glyph_generic)
        surf = glyph_fn()
        path = os.path.join(ICONS_DIR, filename)
        pygame.image.save(surf, path)
        count += 1
    print(f"Generated {count} icons in {ICONS_DIR}")
    return count


# ── Artwork ──────────────────────────────────────────────────────────────────

def _gradient_surface(w: int, h: int,
                      top, bottom) -> pygame.Surface:
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (w, y))
    return surf


def generate_artwork() -> int:
    os.makedirs(ARTWORK_DIR, exist_ok=True)
    count = 0

    # Hero backdrop (1920x420) — violet to charcoal, with a "DEMO" stamp
    hero = _gradient_surface(theme.SCREEN_W, theme.FEATURED_H,
                             (60, 50, 120), (11, 13, 18))
    # Subtle accent line
    pygame.draw.line(hero, theme.ACCENT_PRIMARY,
                     (60, 30), (theme.SCREEN_W - 60, 30), 1)
    pygame.draw.line(hero, theme.ACCENT_PRIMARY,
                     (60, theme.FEATURED_H - 30),
                     (theme.SCREEN_W - 60, theme.FEATURED_H - 30), 1)
    pygame.image.save(hero, os.path.join(ARTWORK_DIR, "hero_demo.png"))
    count += 1

    # Three demo portrait posters (240x360), labelled "DEMO"
    poster_colors = [
        ((40, 60, 110), (90, 70, 160)),
        ((30, 70, 90), (60, 130, 150)),
        ((80, 50, 60), (140, 70, 90)),
    ]
    for i, (c1, c2) in enumerate(poster_colors):
        p = _gradient_surface(theme.CARD_W, theme.CARD_H, c1, c2)
        pygame.image.save(p, os.path.join(ARTWORK_DIR, f"poster_demo_{i + 1}.png"))
        count += 1

    print(f"Generated {count} artwork files in {ARTWORK_DIR}")
    return count


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    what = argv[0] if argv else "all"
    pygame.display.init()  # safe even without a window on most setups
    # If display init fails on a headless box, fall back to dummy driver
    if not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    total = 0
    if what in ("icons", "all"):
        total += generate_icons()
    if what in ("artwork", "all"):
        total += generate_artwork()
    if what not in ("icons", "artwork", "all"):
        print(f"Unknown target '{what}'. Use: icons | artwork | all")
        return 2
    print(f"Done. {total} files generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
