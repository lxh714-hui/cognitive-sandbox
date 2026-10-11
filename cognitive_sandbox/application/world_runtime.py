from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Protocol
from uuid import uuid4

from cognitive_sandbox.domain.actions import ActionProposal, ResolvedAction
from cognitive_sandbox.domain.world_events import WorldEvent


class WorldEventStore(Protocol):
    def append_world_event(self, event: WorldEvent) -> None: ...
    def list_world_events(self, world_id: str) -> list[WorldEvent]: ...


class WorldRuleViolation(ValueError):
    """Raised when an action proposal is not valid in the current world state."""


class WorldRevisionConflict(WorldRuleViolation):
    """Raised when a proposal was based on an outdated world revision."""


class WorldRuntime:
    """Validates action proposals and is the application entry point for WorldEvents."""

    _EVENT_TYPES = {
        "BREAK_OBJECT": "BREAK_OBJECT",
        "INSPECT_OBJECT": "OBJECT_INSPECTED",
    }

    def __init__(
        self,
        event_store: WorldEventStore,
        *,
        world_id: str,
        branch_id: str,
        breakable_object_ids: Iterable[str],
        initial_world_revision: int = 0,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not world_id.strip() or not branch_id.strip():
            raise ValueError("world_id and branch_id must not be empty.")
        if isinstance(initial_world_revision, bool) or not isinstance(initial_world_revision, int):
            raise TypeError("initial_world_revision must be an integer.")
        if initial_world_revision < 0:
            raise ValueError("initial_world_revision must be non-negative.")
        self._event_store = event_store
        self._world_id = world_id
        self._branch_id = branch_id
        self._intact_objects = set(breakable_object_ids)
        self._known_object_ids = set(self._intact_objects)
        self._world_revision = initial_world_revision
        self._event_id_factory = event_id_factory or (lambda: str(uuid4()))

        # Rebuild the small amount of state needed for these rules from committed events.
        for event in event_store.list_world_events(world_id):
            if event.branch_id != branch_id:
                continue
            self._world_revision = max(self._world_revision, event.world_revision)
            if event.event_type in {"BREAK_OBJECT", "OBJECT_INSPECTED"}:
                object_id = event.payload.get("object_id")
                if isinstance(object_id, str):
                    self._known_object_ids.add(object_id)
                    if event.event_type == "BREAK_OBJECT":
                        self._intact_objects.discard(object_id)

    @property
    def world_revision(self) -> int:
        return self._world_revision

    def execute_action(self, resolved_action: ResolvedAction) -> WorldEvent | None:
        """Execute an accepted resolution through the world's normal validation path."""
        if not isinstance(resolved_action, ResolvedAction):
            raise TypeError("resolved_action must be a ResolvedAction.")
        if not resolved_action.accepted:
            return None
        return self.submit_action(resolved_action.action)

    def submit_action(self, proposal: ActionProposal) -> WorldEvent:
        if proposal.world_id != self._world_id or proposal.branch_id != self._branch_id:
            raise WorldRuleViolation("Proposal world or branch does not match this runtime.")
        if proposal.base_world_revision != self._world_revision:
            raise WorldRevisionConflict(
                f"Proposal revision {proposal.base_world_revision} does not match current revision "
                f"{self._world_revision}."
            )
        event_type = self._EVENT_TYPES.get(proposal.action_type)
        if event_type is None:
            raise WorldRuleViolation(f"Unsupported action type: {proposal.action_type}.")
        if proposal.action_type == "BREAK_OBJECT":
            if proposal.target_id is None:
                raise WorldRuleViolation("BREAK_OBJECT requires a target_id.")
            if proposal.target_id not in self._intact_objects:
                raise WorldRuleViolation(f"Object is not available to break: {proposal.target_id}.")
            declared_object_id = proposal.payload.get("object_id")
            if declared_object_id is not None and declared_object_id != proposal.target_id:
                raise WorldRuleViolation("Action payload object_id must match target_id.")
            details = dict(proposal.payload)
            details["object_id"] = proposal.target_id
        else:
            object_id = proposal.payload.get("object_id")
            if not isinstance(object_id, str) or not object_id.strip():
                raise WorldRuleViolation("INSPECT_OBJECT requires payload.object_id.")
            if proposal.target_id is not None and proposal.target_id != object_id:
                raise WorldRuleViolation("INSPECT_OBJECT target_id must match payload.object_id.")
            if object_id not in self._known_object_ids:
                raise WorldRuleViolation(f"Object does not exist: {object_id}.")
            # Inspection events record the action only; descriptive object data stays private.
            details = {"object_id": object_id, "inspector": proposal.actor_id}
        event = WorldEvent(
            event_id=self._event_id_factory(),
            branch_id=proposal.branch_id,
            world_id=proposal.world_id,
            event_type=event_type,
            actor_id=proposal.actor_id,
            payload=details,
            world_revision=self._world_revision + 1,
        )
        # Only consider the action committed once the event has been inserted successfully.
        self._event_store.append_world_event(event)
        self._world_revision = event.world_revision
        if proposal.action_type == "BREAK_OBJECT":
            self._intact_objects.remove(proposal.target_id)
        return event
