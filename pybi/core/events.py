"""Small synchronous event bus for decoupled application modules."""

from collections import defaultdict
from threading import RLock
from typing import Any, Callable, Dict, List


EventHandler = Callable[[Dict[str, Any]], None]


class EventBus:
    """Register and synchronously notify event handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler once for the named event."""
        with self._lock:
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered event handler."""
        with self._lock:
            handlers = self._handlers.get(event_name)
            if handlers and handler in handlers:
                handlers.remove(handler)
                if not handlers:
                    del self._handlers[event_name]

    def publish(self, event_name: str, **payload: Any) -> None:
        """Synchronously deliver an event to a stable snapshot of its handlers."""
        with self._lock:
            handlers = tuple(self._handlers.get(event_name, ()))
        event = {"name": event_name, **payload}
        for handler in handlers:
            handler(event)


event_bus = EventBus()
ETL_EXECUTION_COMPLETED = "etl.execution.completed"
