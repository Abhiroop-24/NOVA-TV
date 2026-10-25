"""
NOVA TV — Main application orchestrator and entry point.

This module wires together every subsystem into a single ``NovaApp`` and
runs the main event/render loop.  It is the only place that owns the
Pygame display and the main loop; everything else is driven through it.

Design:
  • ``NovaApp`` owns config, launcher, media scanner/player, network
    checker, screen manager and input manager.
  • The main loop is intentionally cheap: poll input → update → draw →
    flip, capped to ``theme.FPS_TARGET``.  No filesystem/network work
    happens in the loop.
  • A supervisor wraps the loop so a recoverable exception in a screen
    logs the error, drops the broken screen and shows a recovery screen
    instead of crashing the whole process.
  • ``--dev`` enables a windowed simulation mode that runs on a desktop
    without Raspberry Pi hardware.  Hardware-specific features degrade
    gracefully and are reported on the diagnostics screen.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from typing import Optional

import pygame

from nova import __version__, __app_name__
from nova import theme
from nova.assets import clear_caches
from nova.applications.launcher import AppLauncher
from nova.media.scanner import MediaScanner, MediaPlayer
from nova.navigation.input_manager import InputManager, Action
from nova.settings.config import ConfigManager
from nova.system.diagnostics import (
    NetworkChecker,
    collect_system_info,
    is_raspberry_pi,
)
from nova.ui.screen_manager import ScreenManager

log = logging.getLogger("nova")


# ── Paths ────────────────────────────────────────────────────────────────────

def _project_root() -> str:
    """Directory containing the ``nova`` package (and ``config/``)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _config_path() -> str:
    return os.path.join(_project_root(), "config", "applications.json")


# ── Recovery screen ──────────────────────────────────────────────────────────

class RecoveryScreen:
    """
    Minimal fallback screen shown when a screen raises an exception.

    It is deliberately self-contained (no focus grid, no external assets)
    so that a failure deep in the UI stack cannot recursively fail here.
    """

    name = "Recovery"

    def __init__(self, manager: ScreenManager, message: str):
        self._manager = manager
        self._message = message
        self._pulse = 0.0

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def handle_input(self, action: Action) -> bool:
        if action in (Action.SELECT, Action.BACK, Action.HOME):
            self._manager.go_home()
            return True
        return False

    def update(self, dt: float) -> None:
        self._pulse = (self._pulse + dt * 2.0) % 1.0

    def draw(self, surface: pygame.Surface) -> None:
        from nova.ui import renderer

        surface.fill(theme.BG_DEEP)
        renderer.draw_text(
            surface, "Something went wrong",
            theme.SAFE_MARGIN_X, 200,
            theme.TEXT_PRIMARY, theme.FONT_SIZE_HERO, bold=True,
        )
        renderer.draw_text_wrapped(
            surface,
            self._message,
            theme.SAFE_MARGIN_X, 280,
            max_width=theme.SCREEN_W - 2 * theme.SAFE_MARGIN_X,
            max_lines=4,
            color=theme.TEXT_SECONDARY, size=theme.FONT_SIZE_BODY,
        )
        renderer.draw_text(
            surface, "Press SELECT to return to Home",
            theme.SAFE_MARGIN_X, 480,
            theme.ACCENT_SECONDARY, theme.FONT_SIZE_BODY,
        )


# ── Application ──────────────────────────────────────────────────────────────

class NovaApp:
    """
    The NOVA TV application.

    Construct with :meth:`NovaApp.create`, then call :meth:`run`.
    """

    def __init__(
        self,
        dev: bool = False,
        headless: bool = False,
        enable_cec: bool = True,
        config_dir: Optional[str] = None,
    ):
        self.dev = dev
        self.headless = headless
        self._on_pi = is_raspberry_pi()
        self._debug = False

        # Subsystems (created in create())
        self.config: Optional[ConfigManager] = None
        self.launcher: Optional[AppLauncher] = None
        self.media_scanner: Optional[MediaScanner] = None
        self.media_player: Optional[MediaPlayer] = None
        self.net_checker: Optional[NetworkChecker] = None
        self.input_manager: Optional[InputManager] = None
        self.screens: Optional[ScreenManager] = None

        # Pygame state
        self._screen: Optional[pygame.Surface] = None
        self._clock: Optional[pygame.time.Clock] = None
        self._running = False
        self._frame_count = 0
        self._fps_samples: list[float] = []
        self._enable_cec = enable_cec

        # Cached system values (refreshed off the render path)
        self._cached_ip = ""
        self._ip_checked_at = 0.0
        self._ip_ttl = 30.0  # seconds between IP refreshes

        # Construct config regardless of headless — tests use it directly
        self._config_dir = config_dir

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        dev: bool = False,
        headless: bool = False,
        enable_cec: bool = True,
        config_dir: Optional[str] = None,
    ) -> "NovaApp":
        """Construct and fully initialise a NovaApp (no display yet)."""
        app = cls(dev=dev, headless=headless, enable_cec=enable_cec,
                  config_dir=config_dir)
        app._init_subsystems()
        return app

    def _init_subsystems(self) -> None:
        # Config (persistent settings)
        self.config = ConfigManager(config_dir=self._config_dir)
        self.config.load()

        # Launcher (reads config/applications.json)
        self.launcher = AppLauncher(
            apps_config_path=_config_path(),
            error_callback=lambda src, msg: self.config.log_error(f"app:{src}", msg),
        )
        self.launcher.load()

        # Media scanner + player (driven by config)
        media_dirs = self.config.get("media.directories", [])
        self.media_scanner = MediaScanner(directories=list(media_dirs))
        player_cmd = self.config.get("media.player_command", "mpv")
        self.media_player = MediaPlayer(player_command=player_cmd)

        # Network checker (background thread)
        check_url = self.config.get("network.check_url",
                                    "http://detectportal.firefox.com/success.txt")
        self.net_checker = NetworkChecker(check_url=check_url)

        # Screen manager
        self.screens = ScreenManager()
        self.screens.set_app(self)

    # ── Debug ─────────────────────────────────────────────────────────────────

    @property
    def debug(self) -> bool:
        return self._debug

    def toggle_debug(self) -> None:
        self._debug = not self._debug
        log.info("Debug overlay %s", "on" if self._debug else "off")

    # ── Platform info ─────────────────────────────────────────────────────────

    @property
    def on_raspberry_pi(self) -> bool:
        return self._on_pi

    def system_info(self):
        return collect_system_info()

    def cached_ip(self) -> str:
        """
        Return the local IP address, refreshing at most every ``_ip_ttl``
        seconds.  Screens call this in the render loop instead of doing a
        socket operation every frame.
        """
        now = time.monotonic()
        if not self._cached_ip or (now - self._ip_checked_at) > self._ip_ttl:
            try:
                from nova.system.diagnostics import get_ip_address
                self._cached_ip = get_ip_address()
            except Exception:  # noqa: BLE001 — never block the UI
                self._cached_ip = "127.0.0.1"
            self._ip_checked_at = now
        return self._cached_ip

    # ── Display ───────────────────────────────────────────────────────────────

    def _init_display(self) -> None:
        """Create the Pygame display (skipped in headless mode)."""
        if self.headless:
            # Use a hidden surface so the code path can still be exercised
            # in tests without opening a window.
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            pygame.init()
            # SCALED requires a hardware renderer which the dummy driver
            # doesn't provide — use no flags in headless mode.
            self._screen = pygame.display.set_mode(
                (theme.SCREEN_W, theme.SCREEN_H)
            )
            # Still need a clock for timing in headless mode
            self._clock = pygame.time.Clock()
            return

        pygame.init()
        flags = pygame.SCALED
        fullscreen = bool(self.config.get("display.fullscreen", True)) and not self.dev
        if fullscreen:
            flags |= pygame.FULLSCREEN
        try:
            self._screen = pygame.display.set_mode(
                (theme.SCREEN_W, theme.SCREEN_H), flags, vsync=1
            )
        except pygame.error:
            # vsync not supported — retry without it
            self._screen = pygame.display.set_mode(
                (theme.SCREEN_W, theme.SCREEN_H), flags
            )
        pygame.display.set_caption(f"{__app_name__} {__version__}")
        pygame.mouse.set_visible(False)

        self._clock = pygame.time.Clock()

    # ── Startup / shutdown ────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialise display + services and push the home screen."""
        self._init_display()

        # Start background services
        if self._enable_cec and not self.dev:
            cec = bool(self.config.get("input.enable_cec", True))
        else:
            cec = False
        self.input_manager = InputManager(enable_cec=cec)
        self.net_checker.start()

        # Push the home screen as the root
        from nova.ui.screens.home_screen import HomeScreen
        self.screens.push(HomeScreen(self.screens))

        log.info(
            "%s %s started (dev=%s pi=%s headless=%s)",
            __app_name__, __version__, self.dev, self._on_pi, self.headless,
        )

    def shutdown(self) -> None:
        """Persist state and stop services cleanly."""
        log.info("Shutting down")
        try:
            if self.config:
                self.config.save()
            if self.net_checker:
                self.net_checker.stop()
            if self.input_manager:
                self.input_manager.shutdown()
            if self.media_player:
                self.media_player.stop()
        finally:
            clear_caches()
            pygame.quit()

    # ── Crash recovery ───────────────────────────────────────────────────────

    def _recover(self, exc: BaseException) -> None:
        """Replace the failing screen with a recovery screen."""
        msg = f"{type(exc).__name__}: {exc}"
        log.exception("Screen failure → recovery")
        if self.config:
            self.config.log_error("ui", msg)
        # Drop any pushed screens and show recovery on top of home
        self.screens.go_home()
        self.screens.push(RecoveryScreen(self.screens, msg))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> int:
        """Run until QUIT.  Returns an exit code."""
        if self.screens is None or not self.screens._stack:
            self.start()
        assert self._screen is not None

        self._running = True
        fps_target = int(self.config.get("display.fps_target", theme.FPS_TARGET))
        fps_target = max(15, min(60, fps_target))

        while self._running:
            dt = self._clock.tick(fps_target) / 1000.0 if self._clock else 1 / fps_target
            dt = min(dt, 1.0 / 15.0)  # clamp big stalls
            self._frame(dt)

        self.shutdown()
        return 0

    def _frame(self, dt: float) -> None:
        """
        One frame: poll input → update → draw → flip.

        Self-contained crash recovery: if any step raises, the failing screen
        is replaced by the recovery screen instead of crashing the process.
        This also makes ``_frame`` safe to call directly (used by tests).
        """
        assert self.input_manager is not None
        assert self.screens is not None
        assert self._screen is not None

        try:
            # 1. Input
            actions = self.input_manager.poll()
            for action in actions:
                if action == Action.QUIT:
                    self._running = False
                    return
                self.screens.handle_input(action)

            # 2. Update
            self.screens.update(dt)

            # 3. Draw
            self._screen.fill(theme.BG_DEEP)
            self.screens.draw(self._screen)
            if self._debug:
                self._draw_debug_overlay()
            pygame.display.flip()

            # 4. FPS sampling (cheap, bounded)
            self._frame_count += 1
            if self._clock is not None and self._frame_count % 30 == 0:
                self._fps_samples.append(self._clock.get_fps())
                self._fps_samples = self._fps_samples[-20:]

        except KeyboardInterrupt:
            self._running = False
        except Exception as exc:  # noqa: BLE001 — per-frame supervisor
            self._recover(exc)

    # ── Debug overlay ─────────────────────────────────────────────────────────

    def _draw_debug_overlay(self) -> None:
        from nova.ui import renderer
        assert self._clock is not None

        lines = [
            f"FPS: {self._clock.get_fps():.1f}",
            f"Screen: {self.screens.current.name if self.screens and self.screens.current else '-'}",
            f"Stack: {self.screens.stack_depth if self.screens else 0}",
            f"Pi: {self._on_pi}",
        ]
        if self.net_checker:
            lines.append(f"Net: {'up' if self.net_checker.connected else 'down'}")
        if self.input_manager:
            diag = self.input_manager.diagnostics()
            lines.append(f"CEC: {diag.get('cec_available')}")
            lines.append(f"Joy: {len(diag.get('joysticks', []))}")

        y = 8
        for line in lines:
            renderer.draw_text(
                self._screen, line, 8, y,
                theme.ACCENT_SECONDARY, theme.FONT_SIZE_SMALL,
            )
            y += 18

    # ── Diagnostics accessors (used by diagnostics screen) ────────────────────

    def fps_history(self) -> list[float]:
        return list(self._fps_samples)

    def frame_count(self) -> int:
        return self._frame_count


# ── Supervisor / entry point ─────────────────────────────────────────────────

def _setup_logging(level: str, dev: bool) -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                         format=fmt)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point (referenced by ``pyproject.toml`` as ``nova-tv``)."""
    parser = argparse.ArgumentParser(prog="nova-tv", description="NOVA TV media environment")
    parser.add_argument("--dev", action="store_true",
                        help="Development/simulation mode (windowed, no CEC).")
    parser.add_argument("--headless", action="store_true",
                        help="Run without a visible window (testing).")
    parser.add_argument("--no-cec", action="store_true",
                        help="Disable HDMI-CEC input even on the Pi.")
    parser.add_argument("--config-dir", default=None,
                        help="Override the user config directory.")
    parser.add_argument("--log-level", default="INFO",
                        help="Logging level (DEBUG/INFO/WARNING/ERROR).")
    parser.add_argument("--version", action="version",
                        version=f"{__app_name__} {__version__}")
    args = parser.parse_args(argv)

    _setup_logging(args.log_level, args.dev)
    log.info("Starting %s %s", __app_name__, __version__)

    # Graceful shutdown on SIGTERM (systemd sends this on stop)
    app: Optional[NovaApp] = None

    def _sigterm(_signum, _frame) -> None:
        log.info("Received SIGTERM, stopping")
        if app is not None:
            app._running = False  # noqa: SLF001

    try:
        signal.signal(signal.SIGTERM, _sigterm)
    except (ValueError, AttributeError):
        # Not available on all platforms / contexts
        pass

    try:
        app = NovaApp.create(
            dev=args.dev,
            headless=args.headless,
            enable_cec=not args.no_cec,
            config_dir=args.config_dir,
        )
        return app.run()
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        return 0
    except Exception as exc:  # noqa: BLE001 — top-level safety net
        log.exception("Fatal error: %s", exc)
        return 1
    finally:
        if app is not None:
            try:
                app.shutdown()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    sys.exit(main())
