"""
NOVA TV — Input abstraction layer.

Translates raw SDL / keyboard / CEC events into a small set of semantic
actions that the rest of the UI consumes.  This is the single point of
contact between physical input devices and the navigation system.

Supported backends:
  • Keyboard  — always available (dev + production).
  • HDMI-CEC  — via cec-client pipe (Raspberry Pi only, optional).
  • Joystick  — SDL gamepad/joystick (USB/Bluetooth remotes).

All backends emit Action values; consumers never see raw keycodes.
"""

from __future__ import annotations

import enum
import logging
import subprocess
import threading
import time
from collections import deque
from typing import Deque, Optional

import pygame

from nova import theme

log = logging.getLogger(__name__)


# ── Semantic actions ─────────────────────────────────────────────────────────

class Action(enum.Enum):
    """Every navigation action the UI understands."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    SELECT = "select"
    BACK = "back"
    HOME = "home"
    MENU = "menu"
    PLAY_PAUSE = "play_pause"
    # System
    QUIT = "quit"          # Ctrl-Q or shutdown
    DEBUG_TOGGLE = "debug" # F3
    NONE = "none"


# ── Keyboard mapping ────────────────────────────────────────────────────────

_KEY_MAP: dict[int, Action] = {
    pygame.K_UP:       Action.UP,
    pygame.K_DOWN:     Action.DOWN,
    pygame.K_LEFT:     Action.LEFT,
    pygame.K_RIGHT:    Action.RIGHT,
    pygame.K_RETURN:   Action.SELECT,
    pygame.K_KP_ENTER: Action.SELECT,
    pygame.K_SPACE:    Action.SELECT,
    pygame.K_ESCAPE:   Action.BACK,
    pygame.K_BACKSPACE: Action.BACK,
    pygame.K_HOME:     Action.HOME,
    pygame.K_F1:       Action.HOME,
    pygame.K_F2:       Action.MENU,
    pygame.K_F3:       Action.DEBUG_TOGGLE,
    pygame.K_p:        Action.PLAY_PAUSE,
    # WASD for dev convenience
    pygame.K_w:        Action.UP,
    pygame.K_s:        Action.DOWN,
    pygame.K_a:        Action.LEFT,
    pygame.K_d:        Action.RIGHT,
}

# ── Joystick / gamepad mapping ──────────────────────────────────────────────

_JOY_BUTTON_MAP: dict[int, Action] = {
    0: Action.SELECT,   # A / Cross
    1: Action.BACK,     # B / Circle
    7: Action.HOME,     # Start
    6: Action.MENU,     # Select
}

_JOY_HAT_MAP = {
    (0, 1):  Action.UP,
    (0, -1): Action.DOWN,
    (-1, 0): Action.LEFT,
    (1, 0):  Action.RIGHT,
}

# ── CEC key-name mapping (from cec-client output) ──────────────────────────

_CEC_KEY_MAP: dict[str, Action] = {
    "up":              Action.UP,
    "down":            Action.DOWN,
    "left":            Action.LEFT,
    "right":           Action.RIGHT,
    "select":          Action.SELECT,
    "exit":            Action.BACK,
    "root menu":       Action.HOME,
    "setup menu":      Action.MENU,
    "play":            Action.PLAY_PAUSE,
    "pause":           Action.PLAY_PAUSE,
}


# ── Key repeat logic ────────────────────────────────────────────────────────

class _KeyRepeat:
    """Track held keys and emit repeat actions after a delay."""

    def __init__(self, delay_ms: int, rate_ms: int):
        self._delay = delay_ms
        self._rate = rate_ms
        self._held: dict[Action, float] = {}  # action → timestamp of press
        self._last_repeat: dict[Action, float] = {}

    def press(self, action: Action) -> None:
        now = time.monotonic() * 1000
        self._held[action] = now
        self._last_repeat[action] = now

    def release(self, action: Action) -> None:
        self._held.pop(action, None)
        self._last_repeat.pop(action, None)

    def poll(self) -> list[Action]:
        """Return actions that should repeat this frame."""
        now = time.monotonic() * 1000
        repeats: list[Action] = []
        for action, press_time in list(self._held.items()):
            elapsed = now - press_time
            if elapsed < self._delay:
                continue
            last = self._last_repeat.get(action, press_time)
            if now - last >= self._rate:
                repeats.append(action)
                self._last_repeat[action] = now
        return repeats


# ── CEC listener thread ─────────────────────────────────────────────────────

class _CECListener(threading.Thread):
    """Spawn cec-client and parse its key-press output."""

    daemon = True

    def __init__(self, queue: Deque[Action]):
        super().__init__(name="cec-listener")
        self._queue = queue
        self._proc: Optional[subprocess.Popen] = None
        self._running = False

    @property
    def available(self) -> bool:
        return self._running and self._proc is not None

    def run(self) -> None:
        try:
            self._proc = subprocess.Popen(
                ["cec-client", "-d", "8", "-t", "r"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            self._running = True
            log.info("CEC listener started (pid %d)", self._proc.pid)
        except FileNotFoundError:
            log.info("cec-client not found — CEC input unavailable")
            return
        except Exception as exc:
            log.warning("Failed to start cec-client: %s", exc)
            return

        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            line = line.strip().lower()
            # cec-client prints lines like:  key pressed: up (1)
            if "key pressed:" in line:
                key_part = line.split("key pressed:")[-1].strip()
                key_name = key_part.split("(")[0].strip()
                action = _CEC_KEY_MAP.get(key_name)
                if action:
                    self._queue.append(action)

        self._running = False
        log.info("CEC listener stopped")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()


# ── Public input manager ────────────────────────────────────────────────────

class InputManager:
    """
    Unified input manager.

    Call ``poll()`` once per frame.  It returns a list of Action values
    gathered from keyboard, joystick, CEC, and key-repeat.
    """

    def __init__(self, enable_cec: bool = True):
        self._repeat = _KeyRepeat(theme.INPUT_REPEAT_DELAY, theme.INPUT_REPEAT_RATE)
        self._cec_queue: Deque[Action] = deque(maxlen=32)
        self._cec: Optional[_CECListener] = None
        self._joysticks: list[pygame.joystick.Joystick] = []

        if enable_cec:
            self._cec = _CECListener(self._cec_queue)
            self._cec.start()

        # Init joysticks
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                js = pygame.joystick.Joystick(i)
                js.init()
                self._joysticks.append(js)
                log.info("Joystick %d: %s", i, js.get_name())
        except Exception as exc:
            log.debug("Joystick init: %s", exc)

    # ── Reverse map (for key-up) ────────────────────────────────────────────

    def _action_for_key(self, key: int) -> Action:
        return _KEY_MAP.get(key, Action.NONE)

    # ── Per-frame poll ──────────────────────────────────────────────────────

    def poll(self) -> list[Action]:
        """Process all pending events and return semantic actions."""
        actions: list[Action] = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append(Action.QUIT)

            elif event.type == pygame.KEYDOWN:
                # Ctrl-Q → quit
                if event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL):
                    actions.append(Action.QUIT)
                    continue
                act = self._action_for_key(event.key)
                if act is not Action.NONE:
                    actions.append(act)
                    self._repeat.press(act)

            elif event.type == pygame.KEYUP:
                act = self._action_for_key(event.key)
                if act is not Action.NONE:
                    self._repeat.release(act)

            elif event.type == pygame.JOYBUTTONDOWN:
                act = _JOY_BUTTON_MAP.get(event.button, Action.NONE)
                if act is not Action.NONE:
                    actions.append(act)

            elif event.type == pygame.JOYHATMOTION:
                act = _JOY_HAT_MAP.get(event.value, Action.NONE)
                if act is not Action.NONE:
                    actions.append(act)

            elif event.type == pygame.JOYAXISMOTION:
                # Analogue stick → D-pad (threshold 0.5)
                if abs(event.value) > 0.5:
                    if event.axis == 0:
                        actions.append(Action.RIGHT if event.value > 0 else Action.LEFT)
                    elif event.axis == 1:
                        actions.append(Action.DOWN if event.value > 0 else Action.UP)

        # Key-repeat
        actions.extend(self._repeat.poll())

        # CEC actions
        while self._cec_queue:
            actions.append(self._cec_queue.popleft())

        return actions

    # ── Diagnostics ─────────────────────────────────────────────────────────

    def diagnostics(self) -> dict:
        """Return a dict describing available input devices."""
        info: dict = {
            "keyboard": True,
            "cec_available": self._cec.available if self._cec else False,
            "joysticks": [],
        }
        for js in self._joysticks:
            info["joysticks"].append({
                "name": js.get_name(),
                "axes": js.get_numaxes(),
                "buttons": js.get_numbuttons(),
                "hats": js.get_numhats(),
            })
        return info

    def shutdown(self) -> None:
        if self._cec:
            self._cec.stop()
