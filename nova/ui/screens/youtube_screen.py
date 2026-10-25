"""
NOVA TV — YouTube screen.

Full search → browse → play flow, no browser.
yt-dlp fetches results + stream URLs, mpv plays natively.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  YOUTUBE                          [search bar]       │
  ├─────────────────────────────────────────────────────┤
  │  [result 1 ─ title / channel / duration / views]    │
  │  [result 2]                                          │
  │  ...                                                 │
  └─────────────────────────────────────────────────────┘

Navigation:
  - UP/DOWN scroll through results
  - SELECT on a result → start playback (resolving indicator shown)
  - SELECT on search bar → enter query mode (typing via pygame.KEYDOWN)
  - BACK → return to previous screen
  - During playback: mpv handles its own controls (q to quit)
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import pygame

from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer
from nova.media.youtube import YouTubeSearch, YouTubePlayer, VideoResult, ytdlp_available

log = logging.getLogger(__name__)

# Layout constants
RESULT_H    = 100
RESULT_GAP  = 2
HEADER_H    = 90
SEARCH_H    = 52

ROW_SEARCH  = 0
ROW_RESULTS = 1


class YouTubeScreen(Screen):
    name = "YouTube"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus    = FocusGroup("youtube")
        self._pulse_t  = 0.0

        self._search   = YouTubeSearch(max_results=20)
        self._player: Optional[YouTubePlayer] = None

        self._query        = ""
        self._typing       = False       # keyboard input mode
        self._cursor_blink = 0.0

        self._scroll_y   = 0.0
        self._target_scroll = 0.0

        self._status_msg = ""           # transient status line
        self._error_msg: Optional[str] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        app = self.manager.app
        dev = app.dev if app else True
        self._player = YouTubePlayer(dev_mode=dev)
        self._rebuild_focus()

        if not ytdlp_available():
            self._error_msg = (
                "yt-dlp is not installed.\n"
                "On the Pi: pip install yt-dlp\n"
                "On Windows dev: .venv\\Scripts\\pip install yt-dlp"
            )

    def on_exit(self) -> None:
        # Don't stop playback on exit — user might navigate away while watching
        pass

    # ── Focus grid ────────────────────────────────────────────────────────────

    def _rebuild_focus(self) -> None:
        items: List[FocusItem] = []
        items.append(FocusItem(
            id="search_bar", row=ROW_SEARCH, col=0,
            on_select=self._activate_search,
        ))
        for i, result in enumerate(self._search.results):
            items.append(FocusItem(
                id=f"result_{i}", row=ROW_RESULTS, col=i,
                on_select=lambda idx=i: self._play(idx),
                data=result,
            ))
        self._focus.set_items(items)
        self._focus.focus("search_bar")

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_input(self, action: Action) -> bool:
        # Dismiss error dialog
        if self._error_msg:
            if action in (Action.SELECT, Action.BACK):
                self._error_msg = None
            return True

        # Typing mode — capture keyboard directly
        if self._typing:
            return True  # handled in _handle_typing_event

        if action == Action.SELECT:
            return self._focus.handle(action)
        if action in (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT):
            consumed = self._focus.handle(action)
            self._update_scroll()
            return consumed
        return False

    def handle_pygame_event(self, event: pygame.event.Event) -> bool:
        """Called by the screen manager shim if we're in typing mode."""
        if not self._typing:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._commit_search()
                return True
            elif event.key == pygame.K_ESCAPE:
                self._typing = False
                return True
            elif event.key == pygame.K_BACKSPACE:
                self._query = self._query[:-1]
                return True
            else:
                char = event.unicode
                if char and char.isprintable():
                    self._query += char
                    return True
        return False

    # ── Search actions ────────────────────────────────────────────────────────

    def _activate_search(self) -> None:
        self._typing = True
        self._status_msg = "Type query, press Enter to search"

    def _commit_search(self) -> None:
        self._typing = False
        if not self._query.strip():
            return
        self._status_msg = f"Searching: {self._query}..."
        self._search.search(self._query, on_done=self._on_search_done)

    def _on_search_done(self) -> None:
        if self._search.error:
            self._error_msg = self._search.error
            self._status_msg = ""
        else:
            n = len(self._search.results)
            self._status_msg = f"{n} results" if n else "No results found"
        self._rebuild_focus()
        self._scroll_y = 0
        self._target_scroll = 0

    # ── Playback ──────────────────────────────────────────────────────────────

    def _play(self, idx: int) -> None:
        if not self._player:
            return
        results = self._search.results
        if idx >= len(results):
            return
        video = results[idx]
        self._status_msg = f"Loading: {video.title[:50]}..."
        self._player.play(video, on_exit=self._on_play_exit)

    def _on_play_exit(self) -> None:
        self._status_msg = ""
        if self._player and self._player.error:
            self._error_msg = self._player.error

    # ── Scroll ────────────────────────────────────────────────────────────────

    def _update_scroll(self) -> None:
        focused = self._focus.focused
        if not focused or focused.row == ROW_SEARCH:
            self._target_scroll = 0
            return
        idx = focused.col  # col is item index in results row
        item_y = HEADER_H + idx * (RESULT_H + RESULT_GAP)
        visible_h = theme.SCREEN_H - HEADER_H - theme.STATUS_BAR_H
        # Keep focused item in the middle
        self._target_scroll = max(0, item_y - visible_h // 2)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self._pulse_t     = (self._pulse_t + dt * 2.0) % 1.0
        self._cursor_blink = (self._cursor_blink + dt * 2.0) % 1.0

        diff = self._target_scroll - self._scroll_y
        if abs(diff) > 1:
            self._scroll_y += diff * min(dt * 10, 1.0)
        else:
            self._scroll_y = self._target_scroll

        # Check player for errors that arrive after playback started
        if self._player and not self._player.is_resolving and \
           not self._player.is_playing and self._player.error:
            if not self._error_msg:
                self._error_msg = self._player.error
                self._player._error = None  # noqa: SLF001

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)

        self._draw_header(surface)
        self._draw_results(surface)
        self._draw_statusline(surface)

        if self._error_msg:
            renderer.draw_message_box(surface, "Error",
                                       self._error_msg, "OK", True, self._pulse_t)

    def _draw_header(self, surface: pygame.Surface) -> None:
        # YOUTUBE wordmark
        renderer.draw_text(surface, "YOUTUBE",
                            theme.SAFE_MARGIN_X, 20,
                            theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)

        # Search bar
        bar_x = theme.SAFE_MARGIN_X
        bar_y = 56
        bar_w = theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X
        bar_h = SEARCH_H

        search_focused = self._focus.is_focused("search_bar")

        if search_focused or self._typing:
            pygame.draw.rect(surface, theme.HIGHLIGHT_BG,
                             (bar_x, bar_y, bar_w, bar_h))
            text_color = theme.TEXT_INVERSE
        else:
            pygame.draw.rect(surface, theme.BG_ELEVATED,
                             (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(surface, theme.DIVIDER,
                             (bar_x, bar_y, bar_w, bar_h), 1)
            text_color = theme.TEXT_SECONDARY

        display_query = self._query if self._query else "Search YouTube..."
        if self._typing:
            # Cursor
            cursor = "|" if int(self._cursor_blink * 2) % 2 == 0 else ""
            display_query = self._query + cursor

        renderer.draw_text(surface, display_query,
                            bar_x + 16, bar_y + (bar_h - 20) // 2,
                            text_color, theme.FONT_SIZE_BODY,
                            max_width=bar_w - 32)

        renderer.draw_divider(surface, HEADER_H)

    def _draw_results(self, surface: pygame.Surface) -> None:
        results = self._search.results

        if self._search.is_searching:
            renderer.draw_spinner(surface,
                                   theme.SCREEN_W // 2,
                                   HEADER_H + 120,
                                   self._pulse_t * 3.14, 20)
            renderer.draw_text(surface, "Searching...",
                                theme.SCREEN_W // 2,
                                HEADER_H + 160,
                                theme.TEXT_SECONDARY, theme.FONT_SIZE_BODY,
                                align="center")
            return

        if not results and not self._search.is_searching:
            msg = "Press SELECT on the search bar to find videos"
            if self._search.last_query:
                msg = f"No results for '{self._search.last_query}'"
            renderer.draw_text(surface, msg,
                                theme.SCREEN_W // 2,
                                HEADER_H + 120,
                                theme.TEXT_DISABLED, theme.FONT_SIZE_BODY,
                                align="center")
            return

        # Clip to visible area
        clip = pygame.Rect(0, HEADER_H,
                           theme.SCREEN_W,
                           theme.SCREEN_H - HEADER_H - theme.STATUS_BAR_H)
        surface.set_clip(clip)

        y_base = HEADER_H - int(self._scroll_y)
        for i, video in enumerate(results):
            y = y_base + i * (RESULT_H + RESULT_GAP)
            if y + RESULT_H < HEADER_H or y > theme.SCREEN_H:
                continue
            self._draw_result_row(surface, video, i, y)

        surface.set_clip(None)

        # Resolving overlay
        if self._player and self._player.is_resolving:
            renderer.draw_spinner(surface,
                                   theme.SCREEN_W - theme.SAFE_MARGIN_X - 30,
                                   theme.SCREEN_H - theme.STATUS_BAR_H - 30,
                                   self._pulse_t * 3.14, 14)
            renderer.draw_text(surface, "Loading stream...",
                                theme.SCREEN_W - theme.SAFE_MARGIN_X - 60,
                                theme.SCREEN_H - theme.STATUS_BAR_H - 40,
                                theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL,
                                align="right")

    def _draw_result_row(self, surface: pygame.Surface,
                          video: VideoResult, idx: int, y: int) -> None:
        x  = theme.SAFE_MARGIN_X
        w  = theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X
        h  = RESULT_H
        focused = self._focus.is_focused(f"result_{idx}")

        if focused:
            pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (x, y, w, h))
            title_color = theme.TEXT_INVERSE
            meta_color  = (60, 60, 60)
        else:
            pygame.draw.rect(surface, theme.BG_SURFACE, (x, y, w, h))
            title_color = theme.TEXT_PRIMARY
            meta_color  = theme.TEXT_SECONDARY

        # Index number
        renderer.draw_text(surface, f"{idx + 1:02d}",
                            x + 10, y + RESULT_H // 2 - 10,
                            meta_color, theme.FONT_SIZE_BODY, bold=True)

        # Title
        renderer.draw_text(surface, video.title,
                            x + 52, y + 14,
                            title_color, theme.FONT_SIZE_BODY, bold=True,
                            max_width=w - 300)

        # Meta: channel · duration · views
        parts = []
        if video.channel:
            parts.append(video.channel)
        if video.display_duration:
            parts.append(video.display_duration)
        if video.display_views:
            parts.append(video.display_views)
        meta = "  ·  ".join(parts)
        renderer.draw_text(surface, meta,
                            x + 52, y + 46,
                            meta_color, theme.FONT_SIZE_SMALL,
                            max_width=w - 300)

        # Play arrow on right
        arr_x = x + w - 48
        arr_y = y + RESULT_H // 2
        arr_color = meta_color
        pygame.draw.polygon(surface, arr_color,
                            [(arr_x, arr_y - 10),
                             (arr_x, arr_y + 10),
                             (arr_x + 16, arr_y)])

        # Separator
        if not focused:
            pygame.draw.line(surface, theme.DIVIDER,
                             (x, y + RESULT_H - 1),
                             (x + w, y + RESULT_H - 1), 1)

    def _draw_statusline(self, surface: pygame.Surface) -> None:
        app = self.manager.app
        net_ok = app.net_checker.connected if app and app.net_checker else False
        ip = app.cached_ip() if app else ""
        import time as _time
        renderer.draw_status_bar(
            surface,
            theme.SCREEN_H - theme.STATUS_BAR_H,
            _time.strftime("%H:%M"),
            net_ok, ip,
        )
        if self._status_msg:
            renderer.draw_text(
                surface, self._status_msg,
                theme.SCREEN_W // 2,
                theme.SCREEN_H - theme.STATUS_BAR_H + 5,
                theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL,
                align="center",
            )
