from __future__ import annotations

from dataclasses import dataclass, field
import math
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("Action payload keys must be strings.")
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ActionCandidate:
    action_type: str | None = None
    target_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    action_id: str | None = None
    actor_id: str = "unknown-agent"
    intent: str | None = None
    target: str | None = None
    motivation: str = "unspecified"

    def __post_init__(self) -> None:
        action_type = self.action_type
        if action_type is None and isinstance(self.intent, str):
            action_type = self.intent
        if not isinstance(action_type, str) or not action_type.strip():
            raise ValueError("action_type or intent must not be empty.")
        if isinstance(self.target_refs, str):
            raise TypeError("target_refs must be a collection of target IDs.")
        target_refs = tuple(self.target_refs)
        if any(not isinstance(ref, str) or not ref.strip() for ref in target_refs):
            raise ValueError("target_refs must contain non-empty string IDs.")
        object.__setattr__(self, "target_refs", target_refs)
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        action_id = self.action_id or self.metadata.get("action_id") or f"action_{uuid4().hex}"
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("action_id must not be empty.")
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValueError("actor_id must not be empty.")
        intent = action_type if self.intent is None else self.intent
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must not be empty.")
        target = self.target
        if target is None and target_refs:
            target = target_refs[0]
        if target is not None and (not isinstance(target, str) or not target.strip()):
            raise ValueError("target must be None or a non-empty string.")
        if not target_refs and target is not None:
            target_refs = (target,)
        if not isinstance(self.motivation, str) or not self.motivation.strip():
            raise ValueError("motivation must not be empty.")
        object.__setattr__(self, "action_id", action_id)
        object.__setattr__(self, "action_type", action_type)
        object.__setattr__(self, "target_refs", target_refs)
        object.__setattr__(self, "intent", intent)
        object.__setattr__(self, "target", target)


@dataclass(frozen=True)
class ResolvedActionResult:
    action_id: str
    success: bool
    event_description: str
    impact: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise ValueError("action_id must not be empty.")
        if not isinstance(self.success, bool):
            raise TypeError("success must be a boolean.")
        if not isinstance(self.event_description, str) or not self.event_description.strip():
            raise ValueError("event_description must not be empty.")
        if not isinstance(self.impact, Mapping):
            raise TypeError("impact must be a mapping.")
        object.__setattr__(self, "impact", _freeze(self.impact))


@dataclass(frozen=True)
class ActionScore:
    action_type: str
    score: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, str) or not self.action_type.strip():
            raise ValueError("action_type must not be empty.")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be a number between 0 and 1.")
        if not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        object.__setattr__(self, "score", float(self.score))
        if isinstance(self.reasons, str):
            raise TypeError("reasons must be a collection of explanation strings.")
        reasons = tuple(self.reasons)
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise ValueError("reasons must contain non-empty strings.")
        object.__setattr__(self, "reasons", reasons)


@dataclass(frozen=True)
class ActionProposal:
    """A request to change the objective world; it is not itself a world event."""

    proposal_id: str
    actor_id: str
    action_type: str
    target_id: str | None
    payload: Mapping[str, Any]
    branch_id: str
    world_id: str
    base_world_revision: int
    priority: float = 0.5

    def __post_init__(self) -> None:
        for name in ("proposal_id", "actor_id", "action_type", "branch_id", "world_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.target_id is not None and (not isinstance(self.target_id, str) or not self.target_id.strip()):
            raise ValueError("target_id must be None or a non-empty string.")
        if isinstance(self.base_world_revision, bool) or not isinstance(self.base_world_revision, int):
            raise TypeError("base_world_revision must be an integer.")
        if self.base_world_revision < 0:
            raise ValueError("base_world_revision must be non-negative.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, (int, float)):
            raise TypeError("priority must be a number between 0 and 1.")
        if not math.isfinite(self.priority) or not 0 <= self.priority <= 1:
            raise ValueError("priority must be between 0 and 1.")
        object.__setattr__(self, "priority", float(self.priority))
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping of structured action details.")
        payload = dict(self.payload)
        if self.action_type == "INSPECT_OBJECT" and self.target_id is not None:
            payload.setdefault("object_id", self.target_id)
        object.__setattr__(self, "payload", _freeze(payload))


@dataclass(frozen=True)
class ResolvedAction:
    """Resolution outcome for a proposal; acceptance does not execute the action."""

    action: ActionProposal
    accepted: bool
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.action, ActionProposal):
            raise TypeError("action must be an ActionProposal.")
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be a boolean.")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty.")
