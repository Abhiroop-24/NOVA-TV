"""NOVA TV — Diagnostics screen. Monochrome rebuild."""

from __future__ import annotations
import logging
import time
from typing import List
import pygame
from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer
from nova.system import diagnostics as diag

log = logging.getLogger(__name__)


class DiagnosticsScreen(Screen):
    name = "Diagnostics"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus   = FocusGroup("diag")
        self._pulse_t = 0.0
        self._info    = None
        self._scroll  = 0.0

    def on_enter(self) -> None:
        self._info = diag.collect_system_info()
        self._focus.set_items([FocusItem(
            id="clear", row=0, col=0, on_select=self._clear
        )])
        self._focus.focus("clear")

    def _clear(self) -> None:
        app = self.manager.app
        if app and app.config:
            app.config.clear_errors()
            app.config.save()

    def handle_input(self, action: Action) -> bool:
        if action == Action.DOWN:
            self._scroll = min(self._scroll + 40, 600)
            return True
        if action == Action.UP:
            self._scroll = max(self._scroll - 40, 0)
            return True
        return self._focus.handle(action)

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)

        renderer.draw_text(surface, "DIAGNOSTICS & LOGS",
                           theme.SAFE_MARGIN_X, 30,
                           theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_divider(surface, 75)

        app  = self.manager.app
        info = self._info
        cw   = (theme.SCREEN_W - 3 * theme.SAFE_MARGIN_X) // 2
        x1, x2 = theme.SAFE_MARGIN_X, theme.SAFE_MARGIN_X + cw + theme.SAFE_MARGIN_X
        y = 100

        # Left: metrics
        renderer.draw_section_label(surface, x1, y, "System")
        y += 36
        fps_hist = app.fps_history() if app else []
        avg_fps  = sum(fps_hist) / len(fps_hist) if fps_hist else 0

        for lbl, val in [
            ("Platform",    info.platform if info else "—"),
            ("CPU temp",    f"{info.cpu_temp_c:.1f} C" if info and info.cpu_temp_c else "—"),
            ("Memory",      f"{info.mem_used_mb:.0f}/{info.mem_total_mb:.0f} MB" if info and info.mem_total_mb else "—"),
            ("Free memory", f"{info.mem_available_mb:.0f} MB" if info else "—"),
            ("Disk free",   f"{info.disk_free_gb:.1f} GB" if info and info.disk_free_gb else "—"),
            ("Uptime",      time.strftime("%H:%M:%S", time.gmtime(info.uptime_seconds)) if info else "—"),
            ("Avg FPS",     f"{avg_fps:.1f}" if fps_hist else "—"),
            ("Frames",      str(app.frame_count()) if app else "0"),
        ]:
            renderer.draw_text(surface, lbl, x1, y,
                               theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION)
            renderer.draw_text(surface, val, x1 + 180, y,
                               theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY)
            y += 30

        # FPS sparkline
        if fps_hist:
            sy, sh = y + 10, 36
            pygame.draw.rect(surface, theme.BG_SURFACE, (x1, sy, cw, sh))
            mx = max(max(fps_hist), 1)
            n  = len(fps_hist)
            if n > 1:
                pts = [(x1 + int(i * cw / (n - 1)),
                        sy + sh - int(f / mx * (sh - 4)) - 2)
                       for i, f in enumerate(fps_hist)]
                pygame.draw.lines(surface, theme.TEXT_PRIMARY, False, pts, 1)
            renderer.draw_text(surface, "FPS", x1 + 4, sy + 2,
                               theme.TEXT_DISABLED, theme.FONT_SIZE_SMALL)

        # Right: error log
        y = 100
        renderer.draw_section_label(surface, x2, y, "Recent Errors")
        y += 36
        errors: List = app.config.recent_errors if app and app.config else []

        if not errors:
            renderer.draw_text(surface, "No recent errors.", x2, y,
                               theme.TEXT_DISABLED, theme.FONT_SIZE_CAPTION)
        else:
            for entry in reversed(errors):
                yy = y - int(self._scroll)
                if yy < 90 or yy > theme.SCREEN_H - 120:
                    y += 44
                    continue
                renderer.draw_text(surface, entry.get("time", ""), x2, yy,
                                   theme.TEXT_DISABLED, theme.FONT_SIZE_SMALL)
                renderer.draw_text(surface, entry.get("source", ""), x2 + 160, yy,
                                   theme.TEXT_SECONDARY, theme.FONT_SIZE_SMALL)
                renderer.draw_text_wrapped(
                    surface, entry.get("message", ""),
                    x2, yy + 18, cw, max_lines=2,
                    color=theme.TEXT_PRIMARY, size=theme.FONT_SIZE_SMALL,
                )
                y += 46

        # Clear button
        btn_y = theme.SCREEN_H - theme.STATUS_BAR_H - 60
        bw, bh = 200, 44
        focused = self._focus.is_focused("clear")
        bx = theme.SAFE_MARGIN_X

        if focused:
            pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (bx, btn_y, bw, bh))
            renderer.draw_text(surface, "Clear errors", bx + 20, btn_y + 10,
                               theme.TEXT_INVERSE, theme.FONT_SIZE_BODY)
        else:
            pygame.draw.rect(surface, theme.BG_ELEVATED, (bx, btn_y, bw, bh))
            pygame.draw.rect(surface, theme.DIVIDER, (bx, btn_y, bw, bh), 1)
            renderer.draw_text(surface, "Clear errors", bx + 20, btn_y + 10,
                               theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY)
        if focused:
            renderer.draw_focus_ring(surface, (bx, btn_y, bw, bh))
