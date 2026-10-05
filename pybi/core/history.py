"""History manager for undo and redo operations."""

import copy
from collections import deque
from typing import Any, Deque, Optional


class HistoryManager:
    """Manages undo/redo state stacks for ETL graphs and dashboard layouts."""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.undo_stack: Deque[Any] = deque(maxlen=max_history)
        self.redo_stack: Deque[Any] = deque(maxlen=max_history)
        self.current_state: Optional[Any] = None

    def push_state(self, state: Any) -> None:
        """Push a new state snippet onto the undo stack and clear the redo stack."""
        if self.current_state is not None:
            self.undo_stack.append(copy.deepcopy(self.current_state))
            self.redo_stack.clear()
        self.current_state = copy.deepcopy(state)

    def undo(self) -> Optional[Any]:
        """Restore and return the previous state if available."""
        if not self.can_undo():
            return None
        if self.current_state is not None:
            self.redo_stack.append(copy.deepcopy(self.current_state))
        self.current_state = self.undo_stack.pop()
        return copy.deepcopy(self.current_state)

    def redo(self) -> Optional[Any]:
        """Restore and return the next state if available."""
        if not self.can_redo():
            return None
        if self.current_state is not None:
            self.undo_stack.append(copy.deepcopy(self.current_state))
        self.current_state = self.redo_stack.pop()
        return copy.deepcopy(self.current_state)

    def can_undo(self) -> bool:
        """Return True if an undo operation is possible."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Return True if a redo operation is possible."""
        return len(self.redo_stack) > 0

    def reset(self, initial_state: Optional[Any] = None) -> None:
        """Clear state history and optionally set a new initial state."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_state = copy.deepcopy(initial_state) if initial_state is not None else None
