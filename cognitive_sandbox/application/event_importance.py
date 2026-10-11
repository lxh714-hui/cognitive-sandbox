from __future__ import annotations

from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.world_events import WorldEvent


class EventImportanceEvaluator:
    """Assign deterministic event importance without changing simulation behavior."""

    _EVENT_SCORES = {
        "BREAK_OBJECT": 0.9,
        "OBJECT_BROKEN": 0.9,
        "OBJECT_INSPECTED": 0.45,
    }
    HIGH_THRESHOLD = 0.7
    MEDIUM_THRESHOLD = 0.4

    def evaluate(self, event: WorldEvent) -> EventImportance:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        score = self._EVENT_SCORES.get(event.event_type, 0.2)
        if score >= self.HIGH_THRESHOLD:
            level = "high"
        elif score >= self.MEDIUM_THRESHOLD:
            level = "medium"
        else:
            level = "low"
        return EventImportance(score=score, level=level)
