from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from cognitive_sandbox.event.event_listener import EventListener


@dataclass(frozen=True)
class EventDeliveryError:
    listener_name: str
    event_id: str
    error: str


class EventBus:
    """Synchronous ordered event bus; a failing listener cannot stop delivery."""

    def __init__(self):
        self._listeners: list[EventListener] = []
        self._lock = RLock()
        self._errors: list[EventDeliveryError] = []

    @property
    def listeners(self) -> tuple[EventListener, ...]:
        with self._lock:
            return tuple(self._listeners)

    @property
    def errors(self) -> tuple[EventDeliveryError, ...]:
        with self._lock:
            return tuple(self._errors)

    def subscribe(self, listener, *, name: str | None = None, event_types=()) -> EventListener:
        if isinstance(listener, EventListener):
            entry = listener
        else:
            callback = listener if callable(listener) else getattr(listener, "handle_event", None)
            if not callable(callback):
                raise TypeError("listener must be an EventListener or callable.")
            entry = EventListener(name or getattr(listener, "__class__", type(listener)).__name__, callback, tuple(event_types))
        with self._lock:
            self._listeners.append(entry)
        return entry

    def subscribe_before(self, listener, before: str, *, name: str | None = None, event_types=()) -> EventListener:
        """Register a listener before another named listener, preserving stable fan-out order."""
        if isinstance(listener, EventListener):
            entry = listener
        else:
            callback = listener if callable(listener) else getattr(listener, "handle_event", None)
            if not callable(callback):
                raise TypeError("listener must be an EventListener or callable.")
            entry = EventListener(name or getattr(listener, "__class__", type(listener)).__name__, callback, tuple(event_types))
        with self._lock:
            index = next((i for i, item in enumerate(self._listeners) if item.name == before), len(self._listeners))
            self._listeners.insert(index, entry)
        return entry

    def publish(self, event, context=None, *, exclude=()) -> tuple[tuple[str, object], ...]:
        with self._lock:
            listeners = tuple(self._listeners)
        results = []
        for listener in listeners:
            if listener.name in exclude:
                continue
            if not listener.accepts(event):
                continue
            try:
                results.append((listener.name, listener.callback(event, context)))
            except Exception as error:  # listener failures are isolated by contract
                with self._lock:
                    self._errors.append(EventDeliveryError(listener.name, event.event_id, str(error)))
        return tuple(results)
