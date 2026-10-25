"""
NOVA TV — Screen manager.

Manages a stack of screens.  Each screen is a class with ``handle_input()``,
``update(dt)``, and ``draw(surface)`` methods.

Navigation model:
  • Pushing a screen adds it to the stack.
  • BACK pops the top screen (unless it's the root).
  • HOME clears to the root screen.
"""

from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from nova.navigation.input_manager import Action

if TYPE_CHECKING:
    import pygame

log = logging.getLogger(__name__)


class Screen:
    """Base class for all NOVA TV screens."""

    name: str = "Screen"

    def __init__(self, manager: ScreenManager):
        self.manager = manager

    def on_enter(self) -> None:
        """Called when this screen becomes the top screen."""
        pass

    def on_exit(self) -> None:
        """Called when this screen is popped or covered."""
        pass

    def handle_input(self, action: Action) -> bool:
        """
        Handle a navigation action.

        Return True if the action was consumed.
        """
        return False

    def update(self, dt: float) -> None:
        """
        Update state.  ``dt`` is seconds since last frame.
        """
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """
        Draw this screen to the surface.
        """
        pass


class ScreenManager:
    """
    Stack-based screen manager.

    The bottom screen (index 0) is always the home screen.
    """

    def __init__(self):
        self._stack: List[Screen] = []
        self._app = None  # Reference to NovaApp, set after construction

    def set_app(self, app) -> None:
        """Store a reference to the main NovaApp for cross-cutting access."""
        self._app = app

    @property
    def app(self):
        return self._app

    @property
    def current(self) -> Optional[Screen]:
        return self._stack[-1] if self._stack else None

    @property
    def stack_depth(self) -> int:
        return len(self._stack)

    def push(self, screen: Screen) -> None:
        """Push a new screen onto the stack."""
        if self._stack:
            self._stack[-1].on_exit()
        self._stack.append(screen)
        screen.on_enter()
        log.debug("Screen push → %s (depth %d)", screen.name, len(self._stack))

    def pop(self) -> Optional[Screen]:
        """Pop the top screen.  Never pops the root."""
        if len(self._stack) <= 1:
            return None
        screen = self._stack.pop()
        screen.on_exit()
        if self._stack:
            self._stack[-1].on_enter()
        log.debug("Screen pop ← %s (depth %d)", screen.name, len(self._stack))
        return screen

    def go_home(self) -> None:
        """Clear the stack back to the root screen."""
        while len(self._stack) > 1:
            self._stack.pop().on_exit()
        if self._stack:
            self._stack[0].on_enter()
        log.debug("Screen → Home")

    def replace(self, screen: Screen) -> None:
        """Replace the top screen."""
        if self._stack:
            self._stack[-1].on_exit()
            self._stack[-1] = screen
        else:
            self._stack.append(screen)
        screen.on_enter()

    def handle_input(self, action: Action) -> bool:
        """Route input to the current screen, handling BACK and HOME globally."""
        if action == Action.BACK:
            if len(self._stack) > 1:
                self.pop()
                return True
        elif action == Action.HOME:
            if len(self._stack) > 1:
                self.go_home()
                return True

        if self._stack:
            return self._stack[-1].handle_input(action)
        return False

    def update(self, dt: float) -> None:
        if self._stack:
            self._stack[-1].update(dt)

    def draw(self, surface: 'pygame.Surface') -> None:
        if self._stack:
            self._stack[-1].draw(surface)
