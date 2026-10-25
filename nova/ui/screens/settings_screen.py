"""
NOVA TV — Settings screen. Monochrome rebuild.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import pygame

from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer

log = logging.getLogger(__name__)

ROW_H = 72


@dataclass
class SettingRow:
    id: str
    label: str
    kind: str = "info"
    config_key: str = ""
    options: List[str] = field(default_factory=list)
    hint: str = ""
    action: Optional[Callable[[], None]] = None


class SettingsScreen(Screen):
    name = "Settings"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus   = FocusGroup("settings")
        self._pulse_t = 0.0
        self._rows: List[SettingRow] = []
        self._scroll_y = 0.0
        self._target_scroll = 0.0
        self._dialog: Optional[str] = None
        self._dialog_action: Optional[Callable[[], None]] = None

    def on_enter(self) -> None:
        self._build_rows()

    def _build_rows(self) -> None:
        rows: List[SettingRow] = []

        rows.append(SettingRow(id="hdr_display", label="Display", kind="info", hint="section"))
        rows.append(SettingRow(id="fullscreen", label="Fullscreen interface",
                               kind="toggle", config_key="display.fullscreen"))
        rows.append(SettingRow(id="fps", label="Frame rate",
                               kind="cycle", config_key="display.fps_target",
                               options=["30", "24", "60"]))

        rows.append(SettingRow(id="hdr_media", label="Media", kind="info", hint="section"))
        rows.append(SettingRow(id="player", label="Player command",
                               kind="info", config_key="media.player_command"))
        rows.append(SettingRow(id="rescan", label="Rescan media directories",
                               kind="action", action=self._rescan))

        rows.append(SettingRow(id="hdr_input", label="Input", kind="info", hint="section"))
        rows.append(SettingRow(id="cec", label="HDMI-CEC remote",
                               kind="toggle", config_key="input.enable_cec"))

        rows.append(SettingRow(id="hdr_system", label="System", kind="info", hint="section"))
        rows.append(SettingRow(id="show_fps", label="FPS overlay",
                               kind="toggle", config_key="system.show_fps"))
        rows.append(SettingRow(id="log_level", label="Log level",
                               kind="cycle", config_key="system.log_level",
                               options=["INFO", "DEBUG", "WARNING", "ERROR"]))
        rows.append(SettingRow(id="network", label="Network status",
                               kind="action", action=self._open_network))
        rows.append(SettingRow(id="about", label="About NOVA TV",
                               kind="action", action=self._open_about))
        rows.append(SettingRow(id="diagnostics", label="Diagnostics & logs",
                               kind="action", action=self._open_diagnostics))
        rows.append(SettingRow(id="compat", label="Service compatibility",
                               kind="action", action=self._open_compat))

        rows.append(SettingRow(id="hdr_reset", label="Reset", kind="info", hint="section"))
        rows.append(SettingRow(id="reset", label="Reset settings to defaults",
                               kind="action", action=self._confirm_reset))
        rows.append(SettingRow(id="factory", label="Factory reset",
                               kind="action", action=self._confirm_factory,
                               hint="Erases all configuration"))

        self._rows = rows
        self._build_grid()

    def _build_grid(self) -> None:
        items: List[FocusItem] = []
        for i, row in enumerate(self._rows):
            if row.hint == "section":
                continue
            items.append(FocusItem(
                id=row.id, row=i, col=0,
                on_select=lambda rid=row.id: self._on_select(rid),
                data=row,
            ))
        self._focus.set_items(items)
        if items:
            self._focus.focus(items[0].id)

    def _row_value(self, row: SettingRow) -> str:
        app = self.manager.app
        cfg = app.config if app else None
        if not cfg or not row.config_key:
            return ""
        if row.kind == "toggle":
            return "ON" if cfg.get(row.config_key) else "OFF"
        if row.kind in ("cycle", "info"):
            return str(cfg.get(row.config_key, ""))
        return ""

    def _on_select(self, row_id: str) -> None:
        row = next((r for r in self._rows if r.id == row_id), None)
        if not row:
            return
        app = self.manager.app
        cfg = app.config if app else None
        if not cfg:
            return
        if row.kind == "toggle":
            cur = bool(cfg.get(row.config_key, False))
            cfg.set(row.config_key, not cur)
            cfg.save()
        elif row.kind == "cycle":
            cur  = str(cfg.get(row.config_key, row.options[0] if row.options else ""))
            opts = row.options or [cur]
            try:
                idx = opts.index(cur)
            except ValueError:
                idx = -1
            cfg.set(row.config_key, opts[(idx + 1) % len(opts)])
            cfg.save()
        elif row.kind == "action" and row.action:
            row.action()

    def _rescan(self) -> None:
        app = self.manager.app
        if app and app.media_scanner:
            app.media_scanner.scan_async()

    def _open_network(self) -> None:
        from nova.ui.screens.network_screen import NetworkScreen
        self.manager.push(NetworkScreen(self.manager))

    def _open_about(self) -> None:
        from nova.ui.screens.about_screen import AboutScreen
        self.manager.push(AboutScreen(self.manager))

    def _open_diagnostics(self) -> None:
        from nova.ui.screens.diagnostics_screen import DiagnosticsScreen
        self.manager.push(DiagnosticsScreen(self.manager))

    def _open_compat(self) -> None:
        from nova.ui.screens.compatibility_screen import CompatibilityScreen
        self.manager.push(CompatibilityScreen(self.manager))

    def _confirm_reset(self) -> None:
        self._dialog = "Reset all settings to defaults? Favourites and logs are kept."
        self._dialog_action = self._do_reset

    def _confirm_factory(self) -> None:
        self._dialog = "Factory reset erases ALL config, favourites and logs. Continue?"
        self._dialog_action = self._do_factory

    def _do_reset(self) -> None:
        app = self.manager.app
        if app and app.config:
            app.config.reset_to_defaults()
        self._build_rows()

    def _do_factory(self) -> None:
        app = self.manager.app
        if app and app.config:
            app.config.factory_reset()
        self._build_rows()

    def handle_input(self, action: Action) -> bool:
        if self._dialog is not None:
            if action == Action.SELECT:
                act = self._dialog_action
                self._dialog = None
                self._dialog_action = None
                if act:
                    act()
                return True
            if action == Action.BACK:
                self._dialog = None
                self._dialog_action = None
                return True
            return True
        return self._focus.handle(action)

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0
        focused = self._focus.focused
        if focused:
            self._target_scroll = max(0, focused.row * ROW_H - 300)
        diff = self._target_scroll - self._scroll_y
        if abs(diff) > 1:
            self._scroll_y += diff * min(dt * 8, 1.0)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)

        renderer.draw_text(surface, "SETTINGS",
                            theme.SAFE_MARGIN_X, 30,
                            theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_text(surface, "BACK returns",
                            theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                            theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION, align="right")
        renderer.draw_divider(surface, 75)

        y_base = 90 - int(self._scroll_y)

        for i, row in enumerate(self._rows):
            y = y_base + i * ROW_H
            if y + ROW_H < 0 or y > theme.SCREEN_H:
                continue

            if row.hint == "section":
                renderer.draw_section_label(surface, theme.SAFE_MARGIN_X, y + 16, row.label)
                continue

            item_id = row.id
            focused = self._focus.is_focused(item_id)
            rx = theme.SAFE_MARGIN_X
            rw = theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X
            rect = (rx, y + 4, rw, ROW_H - 8)

            if focused:
                pygame.draw.rect(surface, theme.HIGHLIGHT_BG, rect)
                tc = theme.TEXT_INVERSE
                vc = (80, 80, 80)
            else:
                pygame.draw.rect(surface, theme.BG_SURFACE, rect)
                tc = theme.TEXT_PRIMARY
                vc = theme.TEXT_SECONDARY

            renderer.draw_text(surface, row.label,
                                rx + 20, y + 20, tc, theme.FONT_SIZE_BODY)

            value = self._row_value(row)
            if row.kind == "toggle":
                on_c = theme.STATUS_OK if value == "ON" else (80, 80, 80)
                if focused:
                    on_c = (80, 80, 80) if value == "ON" else (100, 100, 100)
                renderer.draw_text(surface, value,
                                    rx + rw - 20, y + 20,
                                    on_c, theme.FONT_SIZE_BODY, bold=True, align="right")
            elif row.kind == "cycle":
                renderer.draw_text(surface, value,
                                    rx + rw - 20, y + 20,
                                    vc, theme.FONT_SIZE_BODY, align="right")
            elif row.kind == "action":
                renderer.draw_text(surface, ">",
                                    rx + rw - 20, y + 16,
                                    vc, theme.FONT_SIZE_HEADING, align="right")
            elif row.kind == "info" and value:
                renderer.draw_text(surface, value,
                                    rx + rw - 20, y + 20,
                                    vc, theme.FONT_SIZE_BODY, align="right")

            if row.hint and row.kind not in ("section",):
                renderer.draw_text(surface, row.hint,
                                    rx + 20, y + 46,
                                    (60, 60, 60) if focused else theme.TEXT_DISABLED,
                                    theme.FONT_SIZE_SMALL)

            if focused:
                renderer.draw_focus_ring(surface, rect)

        if self._dialog is not None:
            renderer.draw_message_box(surface, "Confirm",
                                       self._dialog, "OK", True, self._pulse_t)
