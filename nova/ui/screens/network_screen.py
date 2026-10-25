"""NOVA TV — Network screen. Monochrome rebuild."""

from __future__ import annotations
import logging
import pygame
from nova import theme
from nova.navigation.input_manager import Action
from nova.navigation.focus import FocusGroup, FocusItem
from nova.ui.screen_manager import Screen, ScreenManager
from nova.ui import renderer
from nova.system import diagnostics as diag

log = logging.getLogger(__name__)


class NetworkScreen(Screen):
    name = "Network"

    def __init__(self, manager: ScreenManager):
        super().__init__(manager)
        self._focus   = FocusGroup("network")
        self._pulse_t = 0.0
        self._info    = None

    def on_enter(self) -> None:
        self._refresh()
        self._focus.set_items([FocusItem(
            id="recheck", row=0, col=0, on_select=self._do_recheck
        )])
        self._focus.focus("recheck")

    def _refresh(self) -> None:
        self._info = diag.collect_system_info()

    def _do_recheck(self) -> None:
        app = self.manager.app
        if app and app.net_checker:
            app.net_checker.check_once()
        self._refresh()

    def handle_input(self, action: Action) -> bool:
        return self._focus.handle(action)

    def update(self, dt: float) -> None:
        self._pulse_t = (self._pulse_t + dt * 2.0) % 1.0

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG_DEEP)
        info = self._info
        app  = self.manager.app
        net_ok = app.net_checker.connected if app and app.net_checker else False

        renderer.draw_text(surface, "NETWORK & DEVICES",
                           theme.SAFE_MARGIN_X, 30,
                           theme.TEXT_PRIMARY, theme.FONT_SIZE_TITLE, bold=True)
        renderer.draw_text(surface, "BACK returns",
                           theme.SCREEN_W - theme.SAFE_MARGIN_X, 38,
                           theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION, align="right")
        renderer.draw_divider(surface, 75)

        x, y = theme.SAFE_MARGIN_X, 100
        dot = theme.STATUS_OK if net_ok else theme.STATUS_ERROR
        pygame.draw.circle(surface, dot, (x + 10, y + 14), 7)
        renderer.draw_text(surface, "Online" if net_ok else "Offline",
                           x + 28, y, theme.TEXT_PRIMARY, theme.FONT_SIZE_HEADING, bold=True)
        y += 52

        for label, value in [
            ("Hostname",    info.hostname if info else "—"),
            ("IP address",  info.ip_address if info else "—"),
            ("Wi-Fi SSID",  diag.get_wifi_ssid() or "—"),
            ("Platform",    info.platform if info else "—"),
            ("Raspberry Pi","Yes" if (info and info.is_raspberry_pi) else "No"),
            ("Pi model",    info.pi_model if info and info.pi_model else "—"),
        ]:
            renderer.draw_text(surface, label, x, y,
                               theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION)
            renderer.draw_text(surface, value, x + 260, y,
                               theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY,
                               max_width=theme.SCREEN_W - x - 260 - theme.SAFE_MARGIN_X)
            y += 36

        y += 16
        renderer.draw_section_label(surface, x, y, "Input Devices")
        y += 36

        if app and app.input_manager:
            ind = app.input_manager.diagnostics()
            for lbl, val in [
                ("Keyboard",   "Available"),
                ("HDMI-CEC",   "Available" if ind.get("cec_available") else "Not detected"),
            ]:
                renderer.draw_text(surface, lbl, x, y,
                                   theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION)
                renderer.draw_text(surface, val, x + 260, y,
                                   theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY)
                y += 34
            for js in ind.get("joysticks", []):
                renderer.draw_text(surface, f"Joystick: {js.get('name','?')}",
                                   x, y, theme.TEXT_SECONDARY, theme.FONT_SIZE_CAPTION)
                renderer.draw_text(surface,
                                   f"{js.get('buttons',0)} btn / {js.get('axes',0)} axes",
                                   x + 260, y, theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY)
                y += 34

        btn_y = theme.SCREEN_H - theme.STATUS_BAR_H - 80
        focused = self._focus.is_focused("recheck")
        bw, bh  = 220, 48
        bx      = theme.SAFE_MARGIN_X

        if focused:
            pygame.draw.rect(surface, theme.HIGHLIGHT_BG, (bx, btn_y, bw, bh))
            renderer.draw_text(surface, "Recheck now",
                                bx + bw // 2, btn_y + 13,
                                theme.TEXT_INVERSE, theme.FONT_SIZE_BODY,
                                bold=True, align="center")
        else:
            pygame.draw.rect(surface, theme.BG_ELEVATED, (bx, btn_y, bw, bh))
            pygame.draw.rect(surface, theme.DIVIDER, (bx, btn_y, bw, bh), 1)
            renderer.draw_text(surface, "Recheck now",
                                bx + bw // 2, btn_y + 13,
                                theme.TEXT_PRIMARY, theme.FONT_SIZE_BODY,
                                align="center")
        if focused:
            renderer.draw_focus_ring(surface, (bx, btn_y, bw, bh))
