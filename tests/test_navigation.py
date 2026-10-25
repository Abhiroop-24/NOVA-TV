"""
NOVA TV — Input manager tests.

Synthesises pygame keyboard events and verifies they map to the correct
semantic Actions.  CEC is disabled so no external process is spawned.
"""

from __future__ import annotations

import pygame
from nova.navigation.input_manager import InputManager, Action


def make_manager():
    return InputManager(enable_cec=False)


def post(key, mod=0, type_=pygame.KEYDOWN):
    pygame.event.post(pygame.event.Event(type_, {"key": key, "mod": mod}))


def drain(manager):
    """Collect all actions from a single poll."""
    return manager.poll()


def test_arrow_keys_map():
    m = make_manager()
    for key, expected in [
        (pygame.K_UP, Action.UP),
        (pygame.K_DOWN, Action.DOWN),
        (pygame.K_LEFT, Action.LEFT),
        (pygame.K_RIGHT, Action.RIGHT),
    ]:
        post(key)
        actions = drain(m)
        assert expected in actions, f"{key} → {actions}"
        # Release to stop key-repeat tracking
        post(key, type_=pygame.KEYUP)
        m.poll()


def test_select_and_back():
    m = make_manager()
    post(pygame.K_RETURN)
    assert Action.SELECT in m.poll()
    post(pygame.K_RETURN, type_=pygame.KEYUP)
    m.poll()
    post(pygame.K_ESCAPE)
    assert Action.BACK in m.poll()
    post(pygame.K_ESCAPE, type_=pygame.KEYUP)
    m.poll()


def test_ctrl_q_quits():
    m = make_manager()
    post(pygame.K_q, mod=pygame.KMOD_CTRL)
    actions = m.poll()
    assert Action.QUIT in actions


def test_quit_event():
    m = make_manager()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    actions = m.poll()
    assert Action.QUIT in actions


def test_unknown_key_is_none():
    m = make_manager()
    # A key not in the map (e.g. F9) should not produce an action
    post(pygame.K_F9)
    actions = m.poll()
    assert all(a != Action.NONE for a in actions)  # NONE never emitted
    post(pygame.K_F9, type_=pygame.KEYUP)
    m.poll()


def test_diagnostics_reports_devices():
    m = make_manager()
    d = m.diagnostics()
    assert "keyboard" in d
    assert "cec_available" in d
    assert d["cec_available"] is False  # CEC disabled
    assert isinstance(d["joysticks"], list)
    m.shutdown()
