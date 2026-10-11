from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from typing import Iterable


def _source_refs(refs: Iterable[str]) -> tuple[str, ...]:
    if isinstance(refs, str):
        raise TypeError("source_refs must be a collection of source IDs, not one string.")
    normalized = tuple(refs)
    if not normalized:
        raise ValueError("source_refs must contain at least one source ID.")
    if any(not isinstance(ref, str) or not ref.strip() for ref in normalized):
        raise ValueError("source_refs must contain non-empty string IDs.")
    return normalized


@dataclass(frozen=True)
class ObservationTask:
    """A single-agent task tied to one committed world event."""

    task_id: str
    observer_id: str
    source_event_id: str
    world_id: str
    branch_id: str
    created_revision: int
    channel: str = "visual"

    def __post_init__(self) -> None:
        for field_name in (
            "task_id", "observer_id", "source_event_id", "world_id", "branch_id", "channel"
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if isinstance(self.created_revision, bool) or not isinstance(self.created_revision, int):
            raise TypeError("created_revision must be an integer.")
        if self.created_revision < 0:
            raise ValueError("created_revision must be non-negative.")


@dataclass(frozen=True)
class ObservationRecord:
    """Information actually perceived by one agent, with its source IDs."""

    observation_id: str
    agent_id: str
    source_refs: tuple[str, ...]
    observed_at: str
    channel: str
    content: str
    uncertainty: float

    def __post_init__(self) -> None:
        for field_name in ("observation_id", "agent_id", "observed_at", "channel", "content"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        object.__setattr__(self, "source_refs", _source_refs(self.source_refs))
        if isinstance(self.uncertainty, bool) or not isinstance(self.uncertainty, (int, float)):
            raise TypeError("uncertainty must be a number between 0 and 1.")
        if not 0 <= self.uncertainty <= 1:
            raise ValueError("uncertainty must be between 0 and 1.")
        object.__setattr__(self, "uncertainty", float(self.uncertainty))


@dataclass(frozen=True, init=False)
class ObservationResult(ObservationRecord):
    """A perception result that retains the event reference and confidence explicitly."""

    event_ref: str
    confidence: float

    def __init__(
        self,
        *,
        observation_id: str,
        agent_id: str,
        event_ref: str,
        observed_at: str,
        channel: str,
        content: str,
        confidence: float,
    ) -> None:
        if not isinstance(event_ref, str) or not event_ref.strip():
            raise ValueError("event_ref must not be empty.")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise TypeError("confidence must be a number between 0 and 1.")
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "observation_id", observation_id)
        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "source_refs", (event_ref,))
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "channel", channel)
        object.__setattr__(self, "content", content)
        object.__setattr__(self, "uncertainty", 1.0 - float(confidence))
        object.__setattr__(self, "event_ref", event_ref)
        object.__setattr__(self, "confidence", float(confidence))
        ObservationRecord.__post_init__(self)


@dataclass(frozen=True)
class PerceptionContext:
    agent_location_id: str
    event_location_id: str
    can_see: bool = True
    can_hear: bool = True
    attention: float = 1.0
    distance_quality: float = 1.0
    lighting_quality: float = 1.0
    ability_quality: float = 1.0
    emotional_focus: float = 1.0

    def __post_init__(self) -> None:
        for name in ("agent_location_id", "event_location_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.can_see, bool) or not isinstance(self.can_hear, bool):
            raise TypeError("can_see and can_hear must be booleans.")
        for name in (
            "attention", "distance_quality", "lighting_quality", "ability_quality", "emotional_focus"
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a quality value between 0 and 1.")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))


@dataclass(frozen=True)
class VisibleObjectFacts:
    """Whitelisted visual facts; owner and hidden history are intentionally absent."""

    object_id: str
    is_broken: bool
    material_visible: str | None = None
    crack_pattern_visible: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.object_id, str) or not self.object_id.strip():
            raise ValueError("object_id must not be empty.")
        if not isinstance(self.is_broken, bool):
            raise TypeError("is_broken must be a boolean.")
        for name in ("material_visible", "crack_pattern_visible"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be None or a non-empty string.")


def record_from_task(
    task: ObservationTask,
    *,
    content: str,
    observed_at: str | None = None,
    observation_id: str,
    uncertainty: float = 0.0,
) -> ObservationRecord:
    """Build a record whose only source is the event named by the task."""
    return ObservationRecord(
        observation_id=observation_id,
        agent_id=task.observer_id,
        source_refs=(task.source_event_id,),
        observed_at=observed_at or datetime.now().astimezone().isoformat(),
        channel=task.channel,
        content=content,
        uncertainty=uncertainty,
    )
