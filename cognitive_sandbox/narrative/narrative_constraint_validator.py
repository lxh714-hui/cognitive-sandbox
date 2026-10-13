from __future__ import annotations

from dataclasses import dataclass

from cognitive_sandbox.character_presence.character_presence import CharacterPresence, PresenceState


@dataclass(frozen=True)
class NarrativeConstraint:
    target: str
    objective: str
    priority: int = 0
    constraints: tuple[str, ...] = ()

    def __post_init__(self):
        for field in ("target", "objective"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ValueError(f"{field} must not be empty.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int) or self.priority < 0:
            raise ValueError("priority must be a non-negative integer.")
        values = tuple(self.constraints)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("constraints must contain non-empty strings.")
        object.__setattr__(self, "constraints", values)


@dataclass(frozen=True)
class ConstraintValidationResult:
    accepted: bool
    reason: str
    required_events: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "required_events", tuple(self.required_events))


class NarrativeConstraintValidator:
    """Accepts director preferences only when they preserve causal travel and entry rules."""

    def validate(self, constraint: NarrativeConstraint, presences=(), *, current_location=None, reachable_locations=()):
        if not isinstance(constraint, NarrativeConstraint):
            raise TypeError("constraint must be NarrativeConstraint.")
        by_id = {item.character_id: item for item in presences if isinstance(item, CharacterPresence)}
        # A target may be a narrative label; a character constraint is checked when it names a known character.
        target = by_id.get(constraint.target)
        if target is None:
            return ConstraintValidationResult(True, "accepted_as_soft_objective")
        requested_teleport = any(
            token in f"{constraint.objective} {' '.join(constraint.constraints)}".casefold()
            for token in ("teleport now", "瞬移出现", "瞬移登场", "立刻瞬移")
        )
        if requested_teleport:
            return ConstraintValidationResult(False, "teleportation_forbidden", ("causal_travel_required",))
        if target.availability in {PresenceState.UNKNOWN, PresenceState.LEFT}:
            return ConstraintValidationResult(True, "deferred_until_entry_conditions", ("satisfy_entry_conditions",))
        if current_location and target.current_location != current_location and target.current_location not in tuple(reachable_locations):
            return ConstraintValidationResult(True, "requires_causal_travel", ("travel_or_meeting_event",))
        return ConstraintValidationResult(True, "accepted")

