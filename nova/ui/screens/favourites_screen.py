"""NOVA TV — Favourites screen. Monochrome rebuild."""

from __future__ import annotations
import logging
from typing import List, Optional
import pygame
from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer

log = logging.getLogger(__name__)


class FavouritesScreen(Screen):
    name = "Favourites"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus   = FocusGroup("favourites")
        self._pulse_t = 0.0
        self._confirm_id: Optional[str] = None

    def on_enter(self) -> None:
        self._build_grid()

    def _build_grid(self) -> None:
        app  = self.manager.app
        favs = app.config.favourites if app and app.config else []
        items = [FocusItem(id=f"fav_{fid}", row=i, col=0,
                            on_select=lambda fid=fid: self._on_select(fid),
                            data=fid)
                 for i, fid in enumerate(favs)]
        self._focus.set_items(items)
        if items:
            self._focus.focus(items[0].id)

    def handle_input(self, action: Action) -> bool:
        if self._confirm_id is not None:
            if action == Action.SELECT:
                self._remove(self._confirm_id)
                self._confirm_id = None
                return True
            if action == Action.BACK:
                self._confirm_id = None
                return True
            return True
        if action == Action.MENU:
            focused = self._focus.focused
            if focused and focused.data:
                self._confirm_id = focused.data
            return True
        return self._focus.handle(action)

    def _on_select(self, fav_id: str) -> None:
        app = self.manager.app
        if not app or not app.launcher:
            return
        entry = app.launcher.get(fav_id)
        if not entry:
            self._confirm_id = fav_id
            return
        if entry.launch_method.value == "internal":
            if entry.id == "settings":
                from nova.ui.screens.settings_screen import SettingsScreen
                self.manager.push(SettingsScreen(self.manager))
            elif entry.id == "local_media":
                from nova.ui.screens.media_screen import MediaScreen
                self.manager.push(MediaScreen(self.manager))
            return
        app.launcher.launch(fav_id)

    def _remove(self, fav_id: str) -> None:
        app = self.manager.app
        if app and app.config:
            app.config.remove_favourite(fav_id)
            app.config.save()
        self._build_grid()

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)
        renderer.draw_text(surface, "FAVOURITES",
                           theme.SAFE_MARGIN_X, 30,
                           theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_text(surface, "MENU removes  |  BACK returns",
                           theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                           theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION, align="right")
        renderer.draw_divider(surface, 75)

        app  = self.manager.app
        favs = app.config.favourites if app and app.config else []

        if not favs:
            renderer.draw_text(surface, "No favourites yet.",
                               theme.SAFE_MARGIN_X, 130,
                               theme.TEXT_SECONDARY, size=theme.FONT_SIZE_BODY)
            renderer.draw_text(surface,
                               "Open Apps, press MENU on any item to add it here.",
                               theme.SAFE_MARGIN_X, 164,
                               theme.TEXT_DISABLED, size=theme.FONT_SIZE_CAPTION)
            return

        rh = 80
        y0 = 100
        for i, fav_id in enumerate(favs):
            y       = y0 + i * rh
            item_id = f"fav_{fav_id}"
            focused = self._focus.is_focused(item_id)
            entry   = app.launcher.get(fav_id) if app and app.launcher else None
            rw = theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X
            rect = (theme.SAFE_MARGIN_X, y, rw, rh - 4)

            if focused:
                pygame.draw.rect(surface, theme.HIGHLIGHT_BG, rect)
                tc, mc = theme.TEXT_INVERSE, (60, 60, 60)
            else:
                pygame.draw.rect(surface, theme.BG_SURFACE, rect)
                tc, mc = theme.TEXT_PRIMARY, theme.TEXT_SECONDARY

            dot_c = theme.TEXT_PRIMARY if entry else theme.STATUS_ERROR
            pygame.draw.circle(surface, dot_c,
                               (theme.SAFE_MARGIN_X + 24, y + rh // 2 - 2), 6)

            if entry:
                renderer.draw_text(surface, entry.name,
                                   theme.SAFE_MARGIN_X + 48, y + 12,
                                   tc, theme.FONT_SIZE_BODY, bold=True)
                renderer.draw_text(surface, entry.description or entry.launch_method.value,
                                   theme.SAFE_MARGIN_X + 48, y + 40,
                                   mc, theme.FONT_SIZE_CAPTION)
            else:
                renderer.draw_text(surface, fav_id,
                                   theme.SAFE_MARGIN_X + 48, y + 12,
                                   tc, theme.FONT_SIZE_BODY, bold=True)
                renderer.draw_text(surface, "No longer configured",
                                   theme.SAFE_MARGIN_X + 48, y + 40,
                                   theme.STATUS_WARN, theme.FONT_SIZE_CAPTION)
            if focused:
                renderer.draw_focus_ring(surface, rect)

        if self._confirm_id is not None:
            renderer.draw_message_box(
                surface, "Remove favourite?",
                f"Remove '{self._confirm_id}' from favourites?",
                "OK", True, self._pulse_t,
            )
