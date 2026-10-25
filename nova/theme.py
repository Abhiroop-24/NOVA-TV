"""
NOVA TV — Theme and visual constants.

Omarchy-inspired monochrome design system.
Pure black, pure white, one accent grey. No colour except status indicators.
Sharp edges, generous whitespace, bold typography. Feels like a premium
purpose-built appliance, not a desktop app.
"""

from __future__ import annotations

# ── Colours — strict monochrome ───────────────────────────────────────────────

# Backgrounds
BG_DEEP      = (0, 0, 0)          # pure black
BG_SURFACE   = (12, 12, 12)       # near-black surface
BG_ELEVATED  = (22, 22, 22)       # slightly lifted surface
BG_CARD      = (18, 18, 18)       # card background

# Text
TEXT_PRIMARY   = (255, 255, 255)  # pure white
TEXT_SECONDARY = (160, 160, 160)  # medium grey
TEXT_DISABLED  = (70, 70, 70)     # dim grey
TEXT_INVERSE   = (0, 0, 0)        # black text on white bg

# Accent — single grey band used sparingly
ACCENT_PRIMARY   = (255, 255, 255)  # white — used for focus/active
ACCENT_SECONDARY = (200, 200, 200)  # light grey — secondary actions
ACCENT_GLOW      = (255, 255, 255, 40)  # white translucent

# Status — minimal colour, only for functional meaning
STATUS_OK      = (180, 255, 180)  # desaturated green
STATUS_WARN    = (255, 220, 120)  # desaturated amber
STATUS_ERROR   = (255, 100, 100)  # desaturated red
STATUS_UNKNOWN = (100, 100, 100)  # grey

# Focus
FOCUS_BORDER     = (255, 255, 255)  # white border
FOCUS_BG         = (255, 255, 255, 15)  # very subtle fill

# Divider
DIVIDER = (35, 35, 35)

# Highlight — white fill for selected items
HIGHLIGHT_BG   = (255, 255, 255)
HIGHLIGHT_TEXT = (0, 0, 0)

# ── Typography ───────────────────────────────────────────────────────────────

FONT_FAMILY = None

FONT_SIZE_HERO     = 52
FONT_SIZE_TITLE    = 34
FONT_SIZE_HEADING  = 24
FONT_SIZE_BODY     = 20
FONT_SIZE_CAPTION  = 16
FONT_SIZE_SMALL    = 13

# ── Layout ───────────────────────────────────────────────────────────────────

SCREEN_W = 1920
SCREEN_H = 1080

SAFE_MARGIN_X = 72
SAFE_MARGIN_Y = 48

CARD_W      = 200
CARD_H      = 300
CARD_GAP    = 16
CARD_RADIUS = 0     # sharp corners — omarchy style

WIDE_CARD_W = 340
WIDE_CARD_H = 80

ROW_HEIGHT = 360
ROW_GAP    = 40
ROW_LABEL_H = 44

NAV_BAR_H   = 56
STATUS_BAR_H = 28

FEATURED_H  = 400

FOCUS_BORDER_W = 2
FOCUS_PADDING  = 4

# ── Animation ────────────────────────────────────────────────────────────────

ANIM_FOCUS_MS    = 80
ANIM_SCROLL_MS   = 150
ANIM_FADE_MS     = 200
ANIM_PRESS_MS    = 60

# ── Performance ──────────────────────────────────────────────────────────────

FPS_TARGET         = 30
INPUT_REPEAT_DELAY = 400
INPUT_REPEAT_RATE  = 120

# ── Icon map ──────────────────────────────────────────────────────────────────

ICON_MAP = {
    "home":       "home.png",
    "apps":       "apps.png",
    "movies":     "movies.png",
    "favourites": "favourites.png",
    "settings":   "settings.png",
    "network":    "network.png",
    "search":     "search.png",
    "play":       "play.png",
    "back":       "back.png",
    "info":       "info.png",
    "error":      "error.png",
    "check":      "check.png",
    "wifi":       "wifi.png",
    "ethernet":   "ethernet.png",
    "bluetooth":  "bluetooth.png",
    "usb":        "usb.png",
    "folder":     "folder.png",
    "file_video": "file_video.png",
    "file_audio": "file_audio.png",
    "cec":        "cec.png",
    "diagnostic": "diagnostic.png",
    "about":      "about.png",
    "clock":      "clock.png",
    "youtube":    "youtube.png",
}
