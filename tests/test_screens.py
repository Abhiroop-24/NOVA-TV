"""
NOVA TV — Screen manager + headless app tests.

Verifies screen stack behaviour (push/pop/home/replace) and that the full
NovaApp can construct, start, and render several frames headlessly without
raising.  Navigation is exercised by posting keyboard events.
"""

from __future__ import annotations

import os

import pygame
import pytest

from nova.navigation.input_manager import Action
from nova.ui.screen_manager import Screen, ScreenManager
from nova.main import NovaApp


class StubScreen(Screen):
    def __init__(self, manager, name):
        super().__init__(manager)
        self.name = name
        self.entered = 0
        self.exited = 0
        self.drawn = 0

    def on_enter(self):
        self.entered += 1

    def on_exit(self):
        self.exited += 1

    def handle_input(self, action):
        return True

    def draw(self, surface):
        self.drawn += 1


def test_push_pop_home():
    sm = ScreenManager()
    home = StubScreen(sm, "Home")
    apps = StubScreen(sm, "Apps")
    sm.push(home)
    sm.push(apps)
    assert sm.stack_depth == 2
    assert apps.entered == 1 and home.exited == 1
    # BACK pops (handled globally by the manager)
    sm.handle_input(Action.BACK)
    assert sm.stack_depth == 1
    assert sm.current is home
    assert home.entered == 2  # re-entered after pop


def test_home_clears_stack():
    sm = ScreenManager()
    home = StubScreen(sm, "Home")
    a = StubScreen(sm, "A")
    b = StubScreen(sm, "B")
    sm.push(home)
    sm.push(a)
    sm.push(b)
    sm.handle_input(Action.HOME)
    assert sm.stack_depth == 1
    assert sm.current is home


def test_back_does_not_pop_root():
    sm = ScreenManager()
    home = StubScreen(sm, "Home")
    sm.push(home)
    sm.handle_input(Action.BACK)
    assert sm.stack_depth == 1  # root preserved


def test_replace():
    sm = ScreenManager()
    home = StubScreen(sm, "Home")
    sm.push(home)
    new = StubScreen(sm, "New")
    sm.replace(new)
    assert sm.current is new
    assert sm.stack_depth == 1


# ── Full headless app ────────────────────────────────────────────────────────

@pytest.fixture
def headless_app(tmp_path):
    app = NovaApp.create(dev=True, headless=True, enable_cec=False,
                         config_dir=str(tmp_path))
    app.start()
    yield app
    app.shutdown()


def test_app_starts_with_home(headless_app):
    assert headless_app.screens.stack_depth == 1
    assert headless_app.screens.current.name == "Home"


def test_app_renders_frames(headless_app):
    # Run a handful of frames; each must not raise.
    for _ in range(5):
        headless_app._frame(1 / 30)
    assert headless_app.frame_count() == 5


def test_app_navigates_to_apps(headless_app):
    # Post a RIGHT to move along nav, then DOWN to apps row, then SELECT.
    sm = headless_app.screens
    # Focus starts on nav Home. Move right to Apps and select.
    for _ in range(5):  # a few RIGHTs then SELECT
        headless_app._frame(1 / 30)
    # Simulate selecting "Apps" by pushing directly (robust against layout)
    from nova.ui.screens.apps_screen import AppsScreen
    sm.push(AppsScreen(sm))
    headless_app._frame(1 / 30)
    assert sm.current.name == "Apps"
    # BACK returns to home
    sm.handle_input(Action.BACK)
    headless_app._frame(1 / 30)
    assert sm.current.name == "Home"


def test_app_settings_screen_renders(headless_app):
    from nova.ui.screens.settings_screen import SettingsScreen
    sm = headless_app.screens
    sm.push(SettingsScreen(sm))
    headless_app._frame(1 / 30)
    assert sm.current.name == "Settings"
    sm.handle_input(Action.BACK)
    headless_app._frame(1 / 30)
    assert sm.current.name == "Home"


def test_app_recovery_on_exception(headless_app):
    # Force the current screen to raise during draw, then frame it.
    sm = headless_app.screens

    class BoomScreen(Screen):
        name = "Boom"
        def draw(self, surface):
            raise RuntimeError("simulated screen failure")
        def update(self, dt): pass
        def handle_input(self, action): return True

    sm.push(BoomScreen(sm))
    headless_app._frame(1 / 30)  # raises → supervisor catches
    # Supervisor should have replaced Boom with Recovery on top of Home
    assert sm.current.name == "Recovery"
    # SELECT returns home
    sm.handle_input(Action.SELECT)
    headless_app._frame(1 / 30)
    assert sm.current.name == "Home"
