from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.actions import ActionCandidate, ResolvedActionResult
from cognitive_sandbox.domain.world_events import WorldEvent


class ActionEventAdapter:
    """Adapt an action outcome into a structured, uncommitted WorldEvent."""

    _EVENT_TYPES = {
        "help": "help_attempt",
        "protect": "protect_attempt",
        "observe": "observe_action",
    }

    def __init__(
        self,
        *,
        world_id: str,
        branch_id: str,
        world_revision: int,
        event_id_factory: Callable[[], str] | None = None,
        location: str | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        for name, value in (("world_id", world_id), ("branch_id", branch_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(world_revision, bool) or not isinstance(world_revision, int):
            raise TypeError("world_revision must be a non-negative integer.")
        if world_revision < 0:
            raise ValueError("world_revision must be non-negative.")
        self._world_id = world_id
        self._branch_id = branch_id
        self._world_revision = world_revision
        self._event_id_factory = event_id_factory or (lambda: str(uuid4()))
        self._location = location
        self._clock = clock

    def adapt(
        self,
        result: ResolvedActionResult,
        action: ActionCandidate,
    ) -> WorldEvent:
        if not isinstance(result, ResolvedActionResult):
            raise TypeError("result must be a ResolvedActionResult.")
        if not isinstance(action, ActionCandidate):
            raise TypeError("action must be an ActionCandidate.")
        if result.action_id != action.action_id:
            raise ValueError("result and action IDs must match.")

        intent = action.intent.casefold()
        if result.success:
            event_type = self._EVENT_TYPES.get(intent)
            if event_type is None:
                raise ValueError("Successful result has an unsupported action intent.")
        else:
            event_type = "action_failed"

        event_id = self._event_id_factory()
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id_factory must return a non-empty string.")
        return WorldEvent(
            event_id=event_id,
            branch_id=self._branch_id,
            world_id=self._world_id,
            event_type=event_type,
            actor_id=action.actor_id,
            payload={
                "description": result.event_description,
                "impact": result.impact,
            },
            world_revision=self._world_revision,
            target_id=action.target,
            location=self._location,
            # Let EventPipeline stamp the event from WorldClock when available.
            timestamp=self._clock() if self._clock is not None else None,
            metadata={"impact": result.impact},
        )
