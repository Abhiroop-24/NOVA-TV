"""NOVA TV — Service compatibility screen. Monochrome rebuild."""

from __future__ import annotations
import logging
from typing import List
import pygame
from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer

log = logging.getLogger(__name__)

_STATUS_C = {
    "verified":    theme.STATUS_OK,
    "experimental":theme.STATUS_WARN,
    "unavailable": theme.STATUS_ERROR,
    "untested":    theme.STATUS_UNKNOWN,
}
ROW_H = 130


class CompatibilityScreen(Screen):
    name = "Compatibility"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus   = FocusGroup("compat")
        self._pulse_t = 0.0
        self._scroll_y = 0.0
        self._target_scroll = 0.0
        self._report: List[dict] = []

    def on_enter(self) -> None:
        app = self.manager.app
        self._report = app.launcher.compatibility_report() if app and app.launcher else []
        items = [FocusItem(id=f"row_{i}", row=i, col=0)
                 for i in range(len(self._report))]
        self._focus.set_items(items)
        if items:
            self._focus.focus(items[0].id)

    def handle_input(self, action: Action) -> bool:
        consumed = self._focus.handle(action)
        focused = self._focus.focused
        if focused:
            self._target_scroll = max(0, focused.row * ROW_H - 200)
        return consumed

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0
        diff = self._target_scroll - self._scroll_y
        if abs(diff) > 1:
            self._scroll_y += diff * min(dt * 8, 1.0)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)
        renderer.draw_text(surface, "SERVICE COMPATIBILITY",
                           theme.SAFE_MARGIN_X, 30,
                           theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_text(surface, "BACK returns",
                           theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                           theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION, align="right")
        renderer.draw_divider(surface, 75)

        # Legend
        lx, ly = theme.SAFE_MARGIN_X, 86
        for key, color in _STATUS_C.items():
            pygame.draw.circle(surface, color, (lx + 8, ly + 8), 5)
            renderer.draw_text(surface, key.capitalize(),
                               lx + 20, ly, theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL)
            lx += 200

        y_base = 120 - int(self._scroll_y)

        for i, row in enumerate(self._report):
            y = y_base + i * (ROW_H + 4)
            if y + ROW_H < 100 or y > theme.SCREEN_H:
                continue

            focused = self._focus.is_focused(f"row_{i}")
            status  = row.get("status", "untested")
            color   = _STATUS_C.get(status, theme.STATUS_UNKNOWN)
            rx = theme.SAFE_MARGIN_X
            rw = theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X
            rect = (rx, y, rw, ROW_H)

            if focused:
                pygame.draw.rect(surface, theme.HIGHLIGHT_BG, rect)
                tc = theme.TEXT_INVERSE
                mc = (60, 60, 60)
            else:
                pygame.draw.rect(surface, theme.BG_SURFACE, rect)
                tc = theme.TEXT_PRIMARY
                mc = theme.TEXT_SECONDARY

            pygame.draw.rect(surface, color, (rx, y, 4, ROW_H))
            pygame.draw.circle(surface, color, (rx + 24, y + 24), 8)

            renderer.draw_text(surface, row.get("name", "Unknown"),
                               rx + 44, y + 12, tc,
                               theme.FONT_SIZE_HEADING, bold=True)
            renderer.draw_text(surface, status.capitalize(),
                               rx + rw - 20, y + 12,
                               color, theme.FONT_SIZE_CAPTION, align="right")
            renderer.draw_text(surface, f"Method: {row.get('method', '—')}",
                               rx + 20, y + 46, mc, theme.FONT_SIZE_CAPTION)
            notes = row.get("notes", "")
            if notes:
                renderer.draw_text_wrapped(
                    surface, f"Notes: {notes}",
                    rx + 20, y + 68, rw - 40, max_lines=2,
                    color=mc, size=theme.FONT_SIZE_SMALL,
                )
            err = row.get("last_error", "")
            if err:
                renderer.draw_text_wrapped(
                    surface, f"Last error: {err}",
                    rx + 20, y + 106, rw - 40, max_lines=1,
                    color=theme.STATUS_ERROR, size=theme.FONT_SIZE_SMALL,
                )
            if focused:
                renderer.draw_focus_ring(surface, rect)
