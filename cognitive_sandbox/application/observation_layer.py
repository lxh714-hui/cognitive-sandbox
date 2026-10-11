from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import (
    ObservationRecord,
    ObservationResult,
    ObservationTask,
    PerceptionContext,
    VisibleObjectFacts,
    record_from_task,
)
from cognitive_sandbox.domain.world_events import WorldEvent


class CommittedWorldEventReader(Protocol):
    def get_world_event(self, event_id: str) -> WorldEvent | None: ...


class ObservationSourceError(ValueError):
    """Raised when an observation task does not refer to a committed matching event."""


class ObservationLayer:
    """Creates per-agent observation tasks from one committed event and a presence snapshot."""

    def __init__(
        self,
        event_reader: CommittedWorldEventReader,
        *,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._event_reader = event_reader
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def create_tasks(
        self,
        source_event_id: str,
        *,
        observer_locations: Mapping[str, str],
    ) -> list[ObservationTask]:
        """Select agents at the event location; the actor directly witnesses their own action."""
        event = self._require_event(source_event_id)
        location_id = event.payload.get("location_id")
        tasks: list[ObservationTask] = []
        for observer_id, observer_location in observer_locations.items():
            if not isinstance(observer_id, str) or not observer_id.strip():
                raise ValueError("observer IDs must be non-empty strings.")
            if not isinstance(observer_location, str) or not observer_location.strip():
                raise ValueError("observer locations must be non-empty strings.")
            is_actor = observer_id == event.actor_id
            is_present = isinstance(location_id, str) and observer_location == location_id
            if not (is_actor or is_present):
                continue
            tasks.append(
                ObservationTask(
                    task_id=self._id_factory(),
                    observer_id=observer_id,
                    source_event_id=event.event_id,
                    world_id=event.world_id,
                    branch_id=event.branch_id,
                    created_revision=event.world_revision,
                    channel="action" if is_actor else "visual",
                )
            )
        return tasks

    def produce(self, task: ObservationTask) -> ObservationRecord:
        """Produce a factual record from only the single source event referenced by task."""
        event = self._require_event(task.source_event_id)
        if (
            event.world_id != task.world_id
            or event.branch_id != task.branch_id
            or event.world_revision != task.created_revision
        ):
            raise ObservationSourceError("Observation task does not match its source event.")
        return record_from_task(
            task,
            content=self._describe(event),
            observation_id=self._id_factory(),
            observed_at=self._clock(),
            uncertainty=0.0,
        )

    def _require_event(self, event_id: str) -> WorldEvent:
        event = self._event_reader.get_world_event(event_id)
        if event is None:
            raise ObservationSourceError(f"No committed world event found for {event_id}.")
        return event

    @staticmethod
    def _describe(event: WorldEvent) -> str:
        if event.event_type == "BREAK_OBJECT":
            object_id = event.payload.get("object_id")
            if isinstance(object_id, str) and object_id:
                return f"{event.actor_id} broke object {object_id}."
        return f"Observed world event: {event.event_type}."


class ObservationRuntime(ObservationLayer):
    """Generate a single agent's sensory result from one committed event."""

    def generate_observation(
        self,
        agent: Agent,
        world_event: WorldEvent,
        *,
        context: PerceptionContext,
        visible_object_facts: VisibleObjectFacts | None = None,
    ) -> list[ObservationRecord]:
        committed = self._require_event(world_event.event_id)
        if committed != world_event:
            raise ObservationSourceError("Observation requires the exact committed world event.")
        if agent.world_id != committed.world_id:
            return []
        if context.agent_location_id != context.event_location_id:
            return []

        object_id = committed.payload.get("object_id")
        if not isinstance(object_id, str) or not object_id.strip():
            return []

        if committed.event_type in {"BREAK_OBJECT", "OBJECT_BROKEN"} and agent.id == committed.actor_id:
            channel = "action"
            content = f"我打碎了物体 {object_id}。"
            confidence = 0.98 * context.attention * context.ability_quality
        elif context.can_see:
            channel = "visual"
            confidence = (
                0.9
                * context.attention
                * context.distance_quality
                * context.lighting_quality
                * context.ability_quality
                * context.emotional_focus
            )
            if committed.event_type in {"BREAK_OBJECT", "OBJECT_BROKEN"}:
                content = f"看到物体 {object_id} 碎裂，碎片散落。"
            elif committed.event_type == "OBJECT_INSPECTED":
                if agent.id == committed.actor_id and visible_object_facts is not None:
                    if visible_object_facts.object_id != object_id:
                        raise ObservationSourceError("Visible facts must match the inspected object.")
                    content = self._describe_visible_object(visible_object_facts)
                else:
                    content = f"看到有人检查物体 {object_id}。"
            else:
                return []
        elif context.can_hear and committed.event_type in {"BREAK_OBJECT", "OBJECT_BROKEN"}:
            channel = "auditory"
            confidence = (
                0.7
                * context.attention
                * context.distance_quality
                * context.ability_quality
                * context.emotional_focus
            )
            content = "听到物体破碎的声音。"
        elif context.can_hear and committed.event_type == "OBJECT_INSPECTED":
            channel = "auditory"
            confidence = (
                0.55
                * context.attention
                * context.distance_quality
                * context.ability_quality
                * context.emotional_focus
            )
            content = f"听到有人检查物体 {object_id}。"
        else:
            return []

        return [
            ObservationResult(
                observation_id=self._id_factory(),
                agent_id=agent.id,
                event_ref=committed.event_id,
                observed_at=self._clock(),
                channel=channel,
                content=content,
                confidence=confidence,
            )
        ]

    @staticmethod
    def _describe_visible_object(facts: VisibleObjectFacts) -> str:
        if not facts.is_broken:
            return f"检查后看到物体 {facts.object_id} 完好。"
        if facts.material_visible == "glass":
            description = f"看到物体 {facts.object_id} 碎裂，玻璃碎片散落在地面。"
        else:
            description = f"看到物体 {facts.object_id} 碎裂，碎片散落在地面。"
        if facts.crack_pattern_visible:
            description += f"裂纹呈{facts.crack_pattern_visible}。"
        return description
