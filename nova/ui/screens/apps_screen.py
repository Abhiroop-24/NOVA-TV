"""
NOVA TV — Applications screen. Monochrome rebuild.
"""

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

CARD_W = 400
CARD_H = 130
COLS   = 4


class AppsScreen(Screen):
    name = "Apps"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus   = FocusGroup("apps")
        self._pulse_t = 0.0
        self._scroll_y = 0.0
        self._target_scroll = 0.0
        self._error: str = ""

    def on_enter(self) -> None:
        self._build_grid()

    def _build_grid(self) -> None:
        items: List[FocusItem] = []
        app = self.manager.app
        if app and app.launcher:
            for i, entry in enumerate(app.launcher.entries):
                row = i // COLS
                col = i % COLS
                items.append(FocusItem(
                    id=f"app_{entry.id}", row=row, col=col,
                    on_select=lambda eid=entry.id: self._launch(eid),
                    data=entry,
                ))
        self._focus.set_items(items)

    def _launch(self, app_id: str) -> None:
        app = self.manager.app
        if not app or not app.launcher:
            return
        entry = app.launcher.get(app_id)
        if not entry:
            return
        if entry.launch_method.value == "internal":
            if entry.id == "settings":
                from nova.ui.screens.settings_screen import SettingsScreen
                self.manager.push(SettingsScreen(self.manager))
            elif entry.id == "local_media":
                from nova.ui.screens.media_screen import MediaScreen
                self.manager.push(MediaScreen(self.manager))
            return
        ok = app.launcher.launch(app_id)
        if not ok and entry.last_error:
            self._error = entry.last_error

    def handle_input(self, action: Action) -> bool:
        if self._error:
            if action in (Action.SELECT, Action.BACK):
                self._error = ""
            return True
        return self._focus.handle(action)

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0
        focused = self._focus.focused
        if focused:
            self._target_scroll = max(0, focused.row * (CARD_H + 12) - 200)
        diff = self._target_scroll - self._scroll_y
        if abs(diff) > 1:
            self._scroll_y += diff * min(dt * 8, 1.0)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)

        renderer.draw_text(surface, "APPLICATIONS",
                            theme.SAFE_MARGIN_X, 30,
                            theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_text(surface, "BACK returns",
                            theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                            theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION, align="right")
        renderer.draw_divider(surface, 75)

        app = self.manager.app
        if not app or not app.launcher:
            renderer.draw_text(surface, "No applications configured.",
                                theme.SAFE_MARGIN_X, 120, theme.TEXT_SECONDARY)
            return

        GAP = 10
        y_off = 90 - int(self._scroll_y)

        for i, entry in enumerate(app.launcher.entries):
            row = i // COLS
            col = i % COLS
            x = theme.SAFE_MARGIN_X + col * (CARD_W + GAP)
            y = y_off + row * (CARD_H + GAP)

            if y + CARD_H < 0 or y > theme.SCREEN_H:
                continue

            item_id = f"app_{entry.id}"
            focused = self._focus.is_focused(item_id)

            if focused:
                pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (x, y, CARD_W, CARD_H))
                tc = theme.TEXT_INVERSE
                mc = (60, 60, 60)
            else:
                pygame.draw.rect(surface, theme.BG_SURFACE, (x, y, CARD_W, CARD_H))
                tc = theme.TEXT_PRIMARY
                mc = theme.TEXT_SECONDARY

            status_c = {
                "verified":     theme.STATUS_OK,
                "experimental": theme.STATUS_WARN,
                "unavailable":  theme.STATUS_ERROR,
                "untested":     theme.STATUS_UNKNOWN,
            }.get(entry.compat_status.value, theme.STATUS_UNKNOWN)

            pygame.draw.rect(surface, status_c, (x, y, 3, CARD_H))

            renderer.draw_text(surface, entry.name,
                                x + 18, y + 16, tc,
                                theme.FONT_SIZE_HEADING, bold=True,
                                max_width=CARD_W - 30)
            renderer.draw_text(surface,
                                entry.description or entry.launch_method.value,
                                x + 18, y + 50, mc,
                                theme.FONT_SIZE_CAPTION,
                                max_width=CARD_W - 30)
            renderer.draw_text(surface,
                                f"{entry.launch_method.value}  |  {entry.compat_status.value}",
                                x + 18, y + 78, mc,
                                theme.FONT_SIZE_SMALL)
            if entry.compat_notes:
                renderer.draw_text(surface, entry.compat_notes,
                                    x + 18, y + 98, mc,
                                    theme.FONT_SIZE_SMALL, max_width=CARD_W - 30)

            if focused:
                renderer.draw_focus_ring(surface, (x, y, CARD_W, CARD_H))

        if self._error:
            renderer.draw_message_box(surface, "Launch Error",
                                       self._error, "OK", True, self._pulse_t)
