from __future__ import annotations

from dataclasses import dataclass

from .conflict_state import ConflictState, ConflictStatus


@dataclass(frozen=True)
class ConflictContext:
    """Character-scoped, read-only conflict signals supplied to Agency."""

    character_id: str
    active_conflicts: tuple[ConflictState, ...]

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        values = tuple(self.active_conflicts)
        if any(not isinstance(item, ConflictState) for item in values):
            raise TypeError("active_conflicts must contain ConflictState values.")
        values = tuple(item for item in values
                       if self.character_id in item.participants
                       and item.status not in {ConflictStatus.RESOLVED, ConflictStatus.TRANSFORMED,
                                               ConflictStatus.ACCEPTED})
        object.__setattr__(self, "active_conflicts", values)

    @classmethod
    def for_character(cls, character_id, conflicts):
        return cls(character_id, tuple(conflicts))


@dataclass(frozen=True)
class ConflictActionCandidate:
    action_type: str
    target: str | None
    conflict_id: str
    priority: float
    reason: str


class ConflictAgencyAdapter:
    """Turn conflict context into optional Agency candidates, never a decision."""

    _actions = {
        "goal_conflict": ("ask", "socialize", "rest"),
        "information_conflict": ("ask", "investigate", "observe"),
        "relationship_conflict": ("socialize", "ask", "rest"),
        "value_conflict": ("ask", "observe", "travel"),
        "resource_conflict": ("organize", "ask", "travel"),
    }

    def candidates_for(self, context: ConflictContext):
        if not isinstance(context, ConflictContext):
            raise TypeError("context must be a ConflictContext.")
        result = []
        for conflict in context.active_conflicts:
            kind = getattr(conflict.type, "value", conflict.type)
            for action_type in self._actions.get(kind, ()):
                targets = tuple(item for item in conflict.participants if item != context.character_id)
                result.append(ConflictActionCandidate(
                    action_type, targets[0] if targets else None, conflict.id,
                    max(0.0, min(1.0, conflict.pressure)),
                    f"回应当前{_public_kind(kind)}矛盾的一个可选方向",
                ))
        return tuple(result)


class LegacyConflictAdapter:
    """Compatibility-only score modifier for legacy conflict-response callers.

    It adjusts an existing candidate's rank. It never selects or executes an
    action; current conflict-aware Agency should prefer response candidates.
    """

    @staticmethod
    def states(context: ConflictContext):
        return context.active_conflicts

    @staticmethod
    def score_modifier(action_type, context: ConflictContext, **signals):
        return LegacyConflictAdapter.legacy_score_modifier(
            action_type, conflicts=context.active_conflicts, **signals,
        )

    @staticmethod
    def legacy_score_modifier(action_type, *, conflicts=(), emotion=None, **_signals):
        """Return a small signed ranking adjustment matching the old API shape."""
        conflicts = tuple(conflicts)
        if not conflicts:
            return 0.0
        kind = str(action_type).casefold()
        severity = max(
            (max(0.0, min(1.0, float(getattr(item, "severity", 0.0)))) for item in conflicts),
            default=0.0,
        )
        fear = _emotion_value(emotion, "fear")
        stress = _emotion_value(emotion, "stress")
        anger = _emotion_value(emotion, "anger")
        # Legacy callers expected emotion to affect the relative score of an
        # existing candidate. Keep this deliberately small and additive.
        if kind in {"ask", "investigate", "negotiate", "socialize"}:
            modifier = severity * (.08 - .12 * fear - .04 * stress)
        elif kind in {"rest", "observe", "travel", "avoid"}:
            modifier = severity * (.06 + .14 * fear + .04 * stress)
        elif kind in {"protect", "escalate", "compete"}:
            modifier = severity * (.04 + .08 * anger - .08 * fear)
        else:
            return 0.0
        return max(-.2, min(.2, modifier))


def _emotion_value(emotion, field):
    value = getattr(emotion, field, 0.0)
    if isinstance(emotion, dict):
        value = emotion.get(field, value)
    return max(0.0, min(1.0, float(value))) if isinstance(value, (int, float)) else 0.0


def _public_kind(kind):
    return {
        "goal_conflict": "目标",
        "information_conflict": "信息",
        "relationship_conflict": "关系",
        "value_conflict": "价值判断",
        "resource_conflict": "资源",
    }.get(kind, "当前")
