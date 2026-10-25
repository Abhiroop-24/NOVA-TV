"""
NOVA TV — Focus movement tests.

Verifies the 2-D D-pad model: within-row movement, wrapping, row-to-row
movement with column memory, and SELECT dispatch.
"""

from __future__ import annotations

from nova.navigation.focus import FocusGroup, FocusItem
from nova.navigation.input_manager import Action


def make_grid(rows: int, cols: int, select_log=None) -> FocusGroup:
    g = FocusGroup("test")
    items = []
    for r in range(rows):
        for c in range(cols):
            items.append(FocusItem(
                id=f"r{r}c{c}", row=r, col=c,
                on_select=(lambda rid=f"r{r}c{c}": select_log.append(rid)) if select_log is not None else None,
            ))
    g.set_items(items)
    return g


def test_focus_first_on_build():
    g = make_grid(2, 3)
    assert g.focused_id == "r0c0"


def test_left_right_within_row():
    g = make_grid(2, 3)
    assert g.handle(Action.RIGHT) and g.focused_id == "r0c1"
    assert g.handle(Action.RIGHT) and g.focused_id == "r0c2"
    # Wrap to start
    assert g.handle(Action.RIGHT) and g.focused_id == "r0c0"
    # Left wraps to end
    assert g.handle(Action.LEFT) and g.focused_id == "r0c2"


def test_up_down_between_rows():
    g = make_grid(3, 3)
    assert g.handle(Action.DOWN) and g.focused_id == "r1c0"
    assert g.handle(Action.DOWN) and g.focused_id == "r2c0"
    # At bottom → not consumed
    assert not g.handle(Action.DOWN)
    assert g.focused_id == "r2c0"
    assert g.handle(Action.UP) and g.focused_id == "r1c0"


def test_column_memory():
    g = make_grid(3, 3)
    # Move to col 2 on row 0
    g.handle(Action.RIGHT)
    g.handle(Action.RIGHT)
    assert g.focused_id == "r0c2"
    # Move down → should remember col 2
    g.handle(Action.DOWN)
    assert g.focused_id == "r1c2"
    g.handle(Action.DOWN)
    assert g.focused_id == "r2c2"
    # Back up preserves memory
    g.handle(Action.UP)
    assert g.focused_id == "r1c2"


def test_select_fires_callback():
    log = []
    g = make_grid(1, 2, select_log=log)
    g.handle(Action.RIGHT)
    assert g.handle(Action.SELECT) is True
    assert log == ["r0c1"]


def test_top_row_up_not_consumed():
    g = make_grid(2, 2)
    # At r0c0, UP should be a no-op (consumed=False) so the screen can react
    assert not g.handle(Action.UP)
    assert g.focused_id == "r0c0"


def test_empty_group_handles_gracefully():
    g = FocusGroup("empty")
    assert not g.handle(Action.RIGHT)
    assert not g.handle(Action.SELECT)


def test_focus_specific_item():
    g = make_grid(2, 2)
    assert g.focus("r1c1")
    assert g.focused_id == "r1c1"
    assert not g.focus("does_not_exist")
