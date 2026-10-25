"""
NOVA TV — Focus management system.

Provides a 2-D spatial focus model suitable for a TV remote / D-pad.
Each screen registers focusable items with positions.  The focus manager
handles directional movement, wrapping rules, and focus memory per screen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from nova.navigation.input_manager import Action

log = logging.getLogger(__name__)


@dataclass
class FocusItem:
    """A single focusable element on screen."""
    id: str
    row: int                # logical row (0 = nav-bar, 1 = featured, …)
    col: int                # logical column within the row
    rect: pygame_rect_like  = field(default_factory=lambda: (0, 0, 0, 0))
    on_select: Optional[Callable[[], None]] = None
    data: Any = None        # arbitrary payload (app entry, media file, …)

    def __hash__(self) -> int:
        return hash(self.id)


# Type alias — we store (x, y, w, h) tuples but can accept pygame.Rect too
pygame_rect_like = Tuple[int, int, int, int]


class FocusGroup:
    """
    A navigable grid of FocusItems organised by (row, col).

    Movement rules:
    • LEFT / RIGHT  → move within the row, wrapping at edges.
    • UP / DOWN     → move between rows, remembering column preference.
    • SELECT        → call the focused item's on_select callback.
    • BACK          → delegated to the screen.
    """

    def __init__(self, name: str = ""):
        self.name = name
        self._items: Dict[str, FocusItem] = {}
        self._grid: Dict[int, List[FocusItem]] = {}   # row → sorted items
        self._focused_id: Optional[str] = None
        self._col_memory: Dict[int, int] = {}  # row → remembered col

    # ── Registration ────────────────────────────────────────────────────────

    def clear(self) -> None:
        self._items.clear()
        self._grid.clear()
        self._focused_id = None
        self._col_memory.clear()

    def add(self, item: FocusItem) -> None:
        self._items[item.id] = item
        row_list = self._grid.setdefault(item.row, [])
        row_list.append(item)
        row_list.sort(key=lambda it: it.col)

    def remove(self, item_id: str) -> None:
        item = self._items.pop(item_id, None)
        if item and item.row in self._grid:
            self._grid[item.row] = [i for i in self._grid[item.row] if i.id != item_id]
            if not self._grid[item.row]:
                del self._grid[item.row]
        if self._focused_id == item_id:
            self._focused_id = None

    def set_items(self, items: List[FocusItem]) -> None:
        """Replace all items at once."""
        self.clear()
        for item in items:
            self.add(item)
        if items:
            self._focused_id = items[0].id

    # ── Focus state ─────────────────────────────────────────────────────────

    @property
    def focused(self) -> Optional[FocusItem]:
        if self._focused_id and self._focused_id in self._items:
            return self._items[self._focused_id]
        return None

    @property
    def focused_id(self) -> Optional[str]:
        return self._focused_id

    def focus(self, item_id: str) -> bool:
        if item_id in self._items:
            self._focused_id = item_id
            item = self._items[item_id]
            self._col_memory[item.row] = item.col
            return True
        return False

    def focus_first(self) -> bool:
        """Focus the first item in the lowest row."""
        if not self._grid:
            return False
        first_row = min(self._grid.keys())
        items = self._grid[first_row]
        if items:
            return self.focus(items[0].id)
        return False

    def focus_row_col(self, row: int, col: int = 0) -> bool:
        """Focus a specific row/col, clamping col if out of range."""
        items = self._grid.get(row)
        if not items:
            return False
        col = max(0, min(col, len(items) - 1))
        return self.focus(items[col].id)

    # ── Navigation ──────────────────────────────────────────────────────────

    def _sorted_rows(self) -> List[int]:
        return sorted(self._grid.keys())

    def handle(self, action: Action) -> bool:
        """
        Process a navigation action.

        Returns True if the action was consumed (focus moved or item selected).
        """
        if not self._items or not self._grid:
            return False

        current = self.focused
        if current is None:
            self.focus_first()
            return True

        if action == Action.SELECT:
            if current.on_select:
                current.on_select()
            return True

        rows = self._sorted_rows()
        row_items = self._grid.get(current.row, [])
        col_idx = next((i for i, it in enumerate(row_items) if it.id == current.id), 0)
        row_idx = rows.index(current.row) if current.row in rows else 0

        if action == Action.LEFT:
            if col_idx > 0:
                return self.focus(row_items[col_idx - 1].id)
            # Wrap to end of row
            return self.focus(row_items[-1].id)

        elif action == Action.RIGHT:
            if col_idx < len(row_items) - 1:
                return self.focus(row_items[col_idx + 1].id)
            # Wrap to start of row
            return self.focus(row_items[0].id)

        elif action == Action.UP:
            self._col_memory[current.row] = col_idx
            if row_idx > 0:
                target_row = rows[row_idx - 1]
                pref_col = self._col_memory.get(target_row, col_idx)
                return self.focus_row_col(target_row, pref_col)
            return False  # At top — let screen handle (e.g. go to nav bar)

        elif action == Action.DOWN:
            self._col_memory[current.row] = col_idx
            if row_idx < len(rows) - 1:
                target_row = rows[row_idx + 1]
                pref_col = self._col_memory.get(target_row, col_idx)
                return self.focus_row_col(target_row, pref_col)
            return False  # At bottom

        return False

    # ── Query ───────────────────────────────────────────────────────────────

    def is_focused(self, item_id: str) -> bool:
        return self._focused_id == item_id

    def rows(self) -> List[int]:
        return self._sorted_rows()

    def items_in_row(self, row: int) -> List[FocusItem]:
        return list(self._grid.get(row, []))

    def all_items(self) -> List[FocusItem]:
        result = []
        for row in self._sorted_rows():
            result.extend(self._grid[row])
        return result

    def __len__(self) -> int:
        return len(self._items)
