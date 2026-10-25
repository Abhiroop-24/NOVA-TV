"""
NOVA TV — Local media screen. Monochrome rebuild.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pygame

from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer
from nova.media.scanner import MediaFile

log = logging.getLogger(__name__)

CARD_W = 340
CARD_H = 88
COLS   = 5


class MediaScreen(Screen):
    name = "Movies"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus    = FocusGroup("media")
        self._pulse_t  = 0.0
        self._scroll_y = 0.0
        self._target_scroll = 0.0
        self._files: List[MediaFile] = []
        self._error: Optional[str] = None

    def on_enter(self) -> None:
        app = self.manager.app
        if app and app.media_scanner and not app.media_scanner.is_scanning:
            app.media_scanner.scan_async()

    def _rebuild_grid(self) -> None:
        items: List[FocusItem] = []
        for i, mf in enumerate(self._files):
            row = i // COLS
            col = i % COLS
            items.append(FocusItem(
                id=f"media_{i}", row=row, col=col,
                on_select=lambda idx=i: self._play(idx),
                data=mf,
            ))
        self._focus.set_items(items)

    def _play(self, idx: int) -> None:
        if idx >= len(self._files):
            return
        mf = self._files[idx]
        app = self.manager.app
        if app and app.media_player:
            ok, err = app.media_player.play(mf.path)
            if not ok:
                self._error = err

    def handle_input(self, action: Action) -> bool:
        if self._error:
            if action in (Action.SELECT, Action.BACK):
                self._error = None
            return True
        return self._focus.handle(action)

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0
        app = self.manager.app
        if app and app.media_scanner:
            new = app.media_scanner.files
            if len(new) != len(self._files):
                self._files = new
                self._rebuild_grid()
            if app.media_scanner.scan_error:
                self._error = app.media_scanner.scan_error

        focused = self._focus.focused
        if focused:
            self._target_scroll = max(0, focused.row * (CARD_H + 8) - 200)
        diff = self._target_scroll - self._scroll_y
        if abs(diff) > 1:
            self._scroll_y += diff * min(dt * 8, 1.0)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)

        renderer.draw_text(surface, "MOVIES & MEDIA",
                            theme.SAFE_MARGIN_X, 30,
                            theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)

        app = self.manager.app
        scanning = app and app.media_scanner and app.media_scanner.is_scanning

        if scanning:
            renderer.draw_text(surface, "Scanning...",
                                theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                                theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION,
                                align="right")
        else:
            renderer.draw_text(surface, f"{len(self._files)} files",
                                theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                                theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION,
                                align="right")

        renderer.draw_divider(surface, 75)

        if not self._files and not scanning:
            renderer.draw_text(surface, "No media files found.",
                                theme.SAFE_MARGIN_X, 120, theme.TEXT_SECONDARY,
                                size=theme.FONT_SIZE_BODY)
            if app and app.config:
                dirs = app.config.get("media.directories", [])
                renderer.draw_text(surface,
                                    f"Searched: {', '.join(dirs) if dirs else 'none'}",
                                    theme.SAFE_MARGIN_X, 155,
                                    theme.TEXT_DISABLED, size=theme.FONT_SIZE_CAPTION)
            if app and app.media_player:
                avail  = app.media_player.player_available()
                status = "installed" if avail else "NOT FOUND"
                color  = theme.STATUS_OK if avail else theme.STATUS_ERROR
                renderer.draw_text(surface, f"mpv: {status}",
                                    theme.SAFE_MARGIN_X, 185,
                                    color, size=theme.FONT_SIZE_CAPTION)
            return

        GAP   = 8
        y_off = 90 - int(self._scroll_y)

        for i, mf in enumerate(self._files):
            row = i // COLS
            col = i % COLS
            x = theme.SAFE_MARGIN_X + col * (CARD_W + GAP)
            y = y_off + row * (CARD_H + GAP)

            if y + CARD_H < 0 or y > theme.SCREEN_H:
                continue

            item_id = f"media_{i}"
            focused = self._focus.is_focused(item_id)

            if focused:
                pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (x, y, CARD_W, CARD_H))
                tc = theme.TEXT_INVERSE
                mc = (60, 60, 60)
            else:
                pygame.draw.rect(surface, theme.BG_SURFACE, (x, y, CARD_W, CARD_H))
                tc = theme.TEXT_PRIMARY
                mc = theme.TEXT_SECONDARY

            # Type indicator bar
            bar_c = theme.TEXT_PRIMARY if mf.is_video else theme.TEXT_SECONDARY
            pygame.draw.rect(surface, bar_c, (x, y, 3, CARD_H))

            renderer.draw_text(surface, mf.display_name,
                                x + 14, y + 12, tc,
                                theme.FONT_SIZE_BODY, bold=True,
                                max_width=CARD_W - 24)
            renderer.draw_text(surface,
                                f"{'VIDEO' if mf.is_video else 'AUDIO'}  {mf.extension.upper()}  {mf.size_display}",
                                x + 14, y + 44, mc, theme.FONT_SIZE_SMALL)

            if focused:
                renderer.draw_focus_ring(surface, (x, y, CARD_W, CARD_H))

        if self._error:
            renderer.draw_message_box(surface, "Playback Error",
                                       self._error, "OK", True, self._pulse_t)
