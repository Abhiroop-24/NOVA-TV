"""NOVA TV — About screen. Monochrome rebuild."""

from __future__ import annotations
import logging
import pygame
from nova import __version__, __app_name__
from nova import theme
from nova.navigation.input_manager import Action
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer

log = logging.getLogger(__name__)


class AboutScreen(Screen):
    name = "About"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._pulse_t = 0.0

    def on_enter(self) -> None:
        pass

    def handle_input(self, action: Action) -> bool:
        if action in (Action.SELECT, Action.BACK):
            self.manager.pop()
            return True
        return action in (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT)

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)

        renderer.draw_text(surface, "ABOUT", theme.SAFE_MARGIN_X, 30,
                           theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_text(surface, "BACK returns",
                           theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                           theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION, align="right")
        renderer.draw_divider(surface, 75)

        x, y = theme.SAFE_MARGIN_X, 110

        renderer.draw_text(surface, "NOVA TV", x, y,
                           theme.TEXT_PRIMARY, theme.FONT_SIZE_HERO, bold=True)
        y += 72
        renderer.draw_text(surface, f"Version {__version__}", x, y,
                           theme.TEXT_SECONDARY, theme.FONT_SIZE_BODY)
        y += 48

        def row(label: str, value: str) -> None:
            nonlocal y
            renderer.draw_text(surface, label, x, y,
                               theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION)
            renderer.draw_text(surface, value, x + 260, y,
                               theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY,
                               max_width=theme.SCREEN_W - x - 260 - theme.SAFE_MARGIN_X)
            y += 36

        row("Target", "Raspberry Pi 3 Model B+ (1 GB RAM)")
        row("Interface", "Pygame / SDL2 native fullscreen")
        row("YouTube", "yt-dlp + mpv (no browser)")
        row("Media", "mpv external player")
        row("Base OS", "Raspberry Pi OS Lite 32-bit")
        row("Service manager", "systemd")
        row("License", "MIT")

        y += 24
        renderer.draw_section_label(surface, x, y, "Feature Status")
        y += 36

        lines = [
            ("D-pad navigation",         "Verified (sim)",      theme.STATUS_OK),
            ("Persistent settings",       "Verified (sim)",      theme.STATUS_OK),
            ("Local media via mpv",       "Verified (sim)",      theme.STATUS_OK),
            ("YouTube via yt-dlp+mpv",    "Verified (sim)",      theme.STATUS_OK),
            ("HDMI-CEC remote",           "Untested on hardware", theme.STATUS_UNKNOWN),
            ("Boot-to-interface",         "Untested on hardware", theme.STATUS_UNKNOWN),
            ("Certified DRM streaming",   "Unavailable on Pi",   theme.STATUS_ERROR),
        ]
        for lbl, val, color in lines:
            pygame.draw.circle(surface, color, (x + 8, y + 11), 5)
            renderer.draw_text(surface, lbl, x + 22, y,
                               theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY)
            renderer.draw_text(surface, val,
                               theme.SCREEN_W - theme.SAFE_MARGIN_X, y,
                               color, theme.FONT_SIZE_CAPTION, align="right")
            y += 32

        y += 16
        renderer.draw_text_wrapped(
            surface,
            "NOVA TV does not store passwords, does not bypass DRM, and does not "
            "substitute unofficial third-party apps for official services. "
            "YouTube works via yt-dlp + mpv — real native playback, no browser.",
            x, y,
            max_width=theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X,
            max_lines=3,
            color=theme.TEXT_DISABLED,
            size=theme.FONT_SIZE_CAPTION,
        )
