from __future__ import annotations

from collections import deque

from cognitive_sandbox.domain.world_events import WorldEvent


class SimulationEventQueue:
    """FIFO queue of committed world events awaiting simulation processing."""

    def __init__(self) -> None:
        self._events: deque[WorldEvent] = deque()

    def push(self, event: WorldEvent) -> None:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        self._events.append(event)

    def pop(self) -> WorldEvent:
        if not self._events:
            raise IndexError("Cannot pop from an empty simulation event queue.")
        return self._events.popleft()

    def peek(self) -> WorldEvent:
        if not self._events:
            raise IndexError("Cannot peek at an empty simulation event queue.")
        return self._events[0]

    def size(self) -> int:
        return len(self._events)
