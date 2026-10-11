from __future__ import annotations

from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.world_events import WorldEvent


class AgentStateUpdater:
    """Return an updated dynamic state from a small event-based rule table."""

    _CHANGES = {
        "help_attempt": {"confidence": 0.05, "motivation": 0.05},
        "protect_attempt": {"confidence": 0.1, "stress": 0.05},
        "observe_action": {"motivation": 0.02},
        "action_failed": {"confidence": -0.1, "stress": 0.1},
    }

    def update(
        self,
        state: AgentDynamicState,
        event: WorldEvent,
    ) -> AgentDynamicState:
        if not isinstance(state, AgentDynamicState):
            raise TypeError("state must be an AgentDynamicState.")
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")

        changes = self._CHANGES.get(event.event_type, {})
        values = {
            "confidence": min(1.0, max(0.0, state.confidence + changes.get("confidence", 0.0))),
            "stress": min(1.0, max(0.0, state.stress + changes.get("stress", 0.0))),
            "motivation": min(1.0, max(0.0, state.motivation + changes.get("motivation", 0.0))),
        }
        return AgentDynamicState(state.character_id, **values)
