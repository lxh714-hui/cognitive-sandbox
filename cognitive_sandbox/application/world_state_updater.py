from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.domain.world_transition import WorldStateTransition


class WorldStateUpdater:
    """Describe a deterministic state delta for one world event."""

    _CHANGES = {
        "help_attempt": {"social_trust": 0.1},
        "protect_attempt": {"danger_level": -0.1},
        "observe_action": {"information_level": 0.1},
        "action_failed": {"failure_count": 1},
    }

    def update(
        self,
        event: WorldEvent,
        current_world_state: Mapping[str, Any],
    ) -> WorldStateTransition:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        if not isinstance(current_world_state, Mapping):
            raise TypeError("current_world_state must be a mapping.")

        changed_state = self._CHANGES.get(event.event_type, {})
        return WorldStateTransition(event.event_id, changed_state)
