"""
NOVA TV — Home screen.

Omarchy-inspired layout: pure black, white type, no colour.
Navigation bar at top, featured section, app row, local media row.
"""

from __future__ import annotations

import time
import logging
from typing import List, Optional

import pygame

from nova import theme
from nova.assets import get_font
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer

log = logging.getLogger(__name__)

NAV_ITEMS = [
    ("Home",       "home"),
    ("YouTube",    "youtube"),
    ("Movies",     "movies"),
    ("Apps",       "apps"),
    ("Settings",   "settings"),
]

NAV_ITEM_W = 180

ROW_NAV      = 0
ROW_FEATURED = 1
ROW_APPS     = 2


class HomeScreen(Screen):
    name = "Home"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus    = FocusGroup("home")
        self._pulse_t  = 0.0
        self._scroll_y = 0.0
        self._target_scroll_y = 0.0
        self._built    = False

    def on_enter(self) -> None:
        if not self._built:
            self._build_focus_grid()
            self._built = True

    # ── Focus grid ────────────────────────────────────────────────────────────

    def _build_focus_grid(self) -> None:
        items: List[FocusItem] = []

        # Row 0: nav bar
        for i, (label, key) in enumerate(NAV_ITEMS):
            items.append(FocusItem(
                id=f"nav_{key}", row=ROW_NAV, col=i,
                on_select=lambda k=key: self._on_nav(k),
            ))

        # Row 1: featured buttons
        items.append(FocusItem(
            id="feat_youtube", row=ROW_FEATURED, col=0,
            on_select=lambda: self._on_nav("youtube"),
        ))
        items.append(FocusItem(
            id="feat_movies", row=ROW_FEATURED, col=1,
            on_select=lambda: self._on_nav("movies"),
        ))
        items.append(FocusItem(
            id="feat_settings", row=ROW_FEATURED, col=2,
            on_select=lambda: self._on_nav("settings"),
        ))

        # Row 2: app launcher entries
        app = self.manager.app
        if app and app.launcher:
            for i, entry in enumerate(app.launcher.entries[:6]):
                items.append(FocusItem(
                    id=f"app_{entry.id}", row=ROW_APPS, col=i,
                    on_select=lambda eid=entry.id: self._on_app(eid),
                    data=entry,
                ))

        self._focus.set_items(items)
        self._focus.focus("nav_home")

    # ── Navigation callbacks ───────────────────────────────────────────────────

    def _on_nav(self, key: str) -> None:
        if key == "home":
            return
        if key == "youtube":
            from nova.ui.screens.youtube_screen import YouTubeScreen
            self.manager.push(YouTubeScreen(self.manager))
        elif key == "movies":
            from nova.ui.screens.media_screen import MediaScreen
            self.manager.push(MediaScreen(self.manager))
        elif key == "apps":
            from nova.ui.screens.apps_screen import AppsScreen
            self.manager.push(AppsScreen(self.manager))
        elif key == "settings":
            from nova.ui.screens.settings_screen import SettingsScreen
            self.manager.push(SettingsScreen(self.manager))

    def _on_app(self, app_id: str) -> None:
        app = self.manager.app
        if not app or not app.launcher:
            return
        entry = app.launcher.get(app_id)
        if entry and entry.launch_method.value == "internal":
            self._on_nav(entry.id)
        elif entry:
            app.launcher.launch(app_id)

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_input(self, action: Action) -> bool:
        if action == Action.DEBUG_TOGGLE:
            app = self.manager.app
            if app:
                app.toggle_debug()
            return True
        return self._focus.handle(action)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0
        diff = self._target_scroll_y - self._scroll_y
        if abs(diff) > 1:
            self._scroll_y += diff * min(dt * 8, 1.0)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)
        self._draw_nav(surface)
        self._draw_featured(surface)
        self._draw_apps_row(surface)
        self._draw_status(surface)

    # ── Nav bar ───────────────────────────────────────────────────────────────

    def _draw_nav(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, theme.BG_DEEP,
                         (0, 0, theme.SCREEN_W, theme.NAV_BAR_H))

        # Wordmark
        renderer.draw_text(surface, "NOVA TV",
                            theme.SAFE_MARGIN_X, 14,
                            theme.TEXT_PRIMARY, theme.FONT_SIZE_HEADING, bold=True)

        x = theme.SAFE_MARGIN_X + 220
        for i, (label, key) in enumerate(NAV_ITEMS):
            item_id = f"nav_{key}"
            focused = self._focus.is_focused(item_id)
            active  = (key == "home")
            renderer.draw_nav_item(
                surface, x, 4, NAV_ITEM_W, theme.NAV_BAR_H - 8,
                label, focused=focused, active=active,
            )
            x += NAV_ITEM_W + 4

        pygame.draw.line(surface, theme.DIVIDER,
                         (0, theme.NAV_BAR_H - 1),
                         (theme.SCREEN_W, theme.NAV_BAR_H - 1), 1)

    # ── Featured ──────────────────────────────────────────────────────────────

    def _draw_featured(self, surface: pygame.Surface) -> None:
        fy = theme.NAV_BAR_H
        fh = theme.FEATURED_H

        pygame.draw.rect(surface, theme.BG_DEEP, (0, fy, theme.SCREEN_W, fh))

        # Big wordmark / hero
        renderer.draw_text(
            surface, "NOVA", theme.SAFE_MARGIN_X, fy + 60,
            theme.TEXT_PRIMARY, 120, bold=True,
        )
        renderer.draw_text(
            surface, "TV", theme.SAFE_MARGIN_X + 340, fy + 100,
            theme.TEXT_SECONDARY, 80,
        )

        # Tagline
        renderer.draw_text(
            surface,
            "Your media. Your way.",
            theme.SAFE_MARGIN_X, fy + 210,
            theme.TEXT_SECONDARY, theme.FONT_SIZE_HEADING,
        )

        # Action buttons
        btns = [
            ("feat_youtube",  "YouTube"),
            ("feat_movies",   "Movies"),
            ("feat_settings", "Settings"),
        ]
        bx = theme.SAFE_MARGIN_X
        by = fy + fh - 90
        bw, bh = 200, 52

        for item_id, label in btns:
            focused = self._focus.is_focused(item_id)
            if focused:
                pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (bx, by, bw, bh))
                renderer.draw_text(surface, label,
                                    bx + bw // 2, by + 14,
                                    theme.TEXT_INVERSE, theme.FONT_SIZE_BODY,
                                    bold=True, align="center")
            else:
                pygame.draw.rect(surface, theme.BG_ELEVATED, (bx, by, bw, bh))
                pygame.draw.rect(surface, theme.DIVIDER, (bx, by, bw, bh), 1)
                renderer.draw_text(surface, label,
                                    bx + bw // 2, by + 14,
                                    theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY,
                                    align="center")
            if focused:
                renderer.draw_focus_ring(surface, (bx, by, bw, bh))
            bx += bw + 16

        pygame.draw.line(surface, theme.DIVIDER,
                         (0, fy + fh - 1),
                         (theme.SCREEN_W, fy + fh - 1), 1)

    # ── Apps row ──────────────────────────────────────────────────────────────

    def _draw_apps_row(self, surface: pygame.Surface) -> None:
        y_base = theme.NAV_BAR_H + theme.FEATURED_H + 20
        app = self.manager.app
        if not app or not app.launcher:
            return

        renderer.draw_text(surface, "APPLICATIONS",
                            theme.SAFE_MARGIN_X, y_base,
                            theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL, bold=True)

        x = theme.SAFE_MARGIN_X
        y = y_base + 28
        card_w, card_h = 260, 72

        for i, entry in enumerate(app.launcher.entries[:6]):
            item_id = f"app_{entry.id}"
            focused = self._focus.is_focused(item_id)

            status_c = {
                "verified":     theme.STATUS_OK,
                "experimental": theme.STATUS_WARN,
                "unavailable":  theme.STATUS_ERROR,
                "untested":     theme.STATUS_UNKNOWN,
            }.get(entry.compat_status.value, theme.STATUS_UNKNOWN)

            renderer.draw_wide_card(surface, (x, y, card_w, card_h),
                                     label=entry.name,
                                     sublabel=entry.compat_status.value,
                                     focused=focused,
                                     pulse_t=self._pulse_t,
                                     status_color=status_c)
            x += card_w + 8
            if x + card_w > theme.SCREEN_W - theme.SAFE_MARGIN_X:
                break

    # ── Status bar ────────────────────────────────────────────────────────────

    def _draw_status(self, surface: pygame.Surface) -> None:
        app = self.manager.app
        net_ok = app.net_checker.connected if app and app.net_checker else False
        ip     = app.cached_ip() if app else ""
        renderer.draw_status_bar(
            surface,
            theme.SCREEN_H - theme.STATUS_BAR_H,
            time.strftime("%H:%M"),
            net_ok, ip,
        )
