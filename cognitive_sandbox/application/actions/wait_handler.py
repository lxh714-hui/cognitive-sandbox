from __future__ import annotations

from uuid import uuid4

from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.domain.world_events import WorldEvent


class WaitHandler:
    """Advance a small deterministic interval without involving language models."""

    def __init__(self, *, minutes: int = 10, id_factory=None) -> None:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("minutes must be a positive integer")
        self.minutes = minutes
        self._id_factory = id_factory or (lambda: uuid4().hex)

    def handle(self, action, context) -> RoleplayResult:
        event_id = f"event_{self._id_factory()}"
        state = dict(context.world_state)
        state["elapsed_minutes"] = state.get("elapsed_minutes", 0) + self.minutes
        clock = getattr(context, "world_clock", None)
        tick_time = clock.advance(self.minutes) if clock is not None else None
        changes = {}
        if isinstance(state.get("energy_level"), (int, float)) and not isinstance(state.get("energy_level"), bool):
            updated = max(0.0, float(state["energy_level"]) - 0.01)
            changes["energy_level"] = updated
            state["energy_level"] = updated
        event = WorldEvent(
            event_id, context.branch_id, context.world_id, "wait_elapsed",
            action.actor_id,
            {"minutes": self.minutes, "description": f"{self.minutes}分钟过去，远处的声响几度变化，世界仍在向前。", "changes": changes},
            0,
            timestamp=tick_time.isoformat() if tick_time is not None else None,
        )
        events = [event]
        if clock is not None:
            events.append(WorldEvent(
                f"event_{self._id_factory()}", context.branch_id, context.world_id, "world_tick",
                action.actor_id, {"elapsed_minutes": self.minutes}, 0,
                timestamp=tick_time.isoformat(),
            ))
        narrative = NarrativeEvent(event_id, "等待片刻", f"你等待了一段时间。\n{event.payload['description']}", ())
        snapshot = SimulationTickResult(state, context.agent_context, tuple(events))
        return RoleplayResult(context.turn.turn_id, True, (narrative,), (), snapshot)
