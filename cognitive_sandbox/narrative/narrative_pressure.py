from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NarrativePressure:
    urgency: float = 0.0
    danger: float = 0.0
    unresolved_degree: float = 0.0
    trend: str = "stable"
    goal_stagnation: float = 0.0
    conflict_pressure: float = 0.0

    def __post_init__(self):
        for field in ("urgency", "danger", "unresolved_degree", "goal_stagnation", "conflict_pressure"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{field} must be between 0 and 1.")
            object.__setattr__(self, field, float(value))
        if self.trend not in {"rising", "stable", "falling"}:
            raise ValueError("trend must be rising, stable, or falling.")


class NarrativePressureCalculator:
    def calculate(self, conflicts=(), *, danger=0.0, unresolved_count=None, previous=None,
                  goal_stagnation=0.0):
        conflicts = tuple(conflicts)
        urgency = min(1.0, sum(getattr(item, "pressure", 0.0) for item in conflicts) / 3.0)
        unresolved = min(1.0, (len(conflicts) if unresolved_count is None else unresolved_count) / 5.0)
        danger = float(danger) if isinstance(danger, (int, float)) and not isinstance(danger, bool) else 0.0
        danger = min(1.0, max(0.0, danger))
        score = (urgency + danger + unresolved) / 3
        old = (previous.urgency + previous.danger + previous.unresolved_degree) / 3 if previous else score
        trend = "rising" if score > old + 0.03 else "falling" if score < old - 0.03 else "stable"
        goal_stagnation = min(1.0, max(0.0, float(goal_stagnation)))
        urgency = max(urgency, .25 * goal_stagnation)
        unresolved = max(unresolved, .35 * goal_stagnation)
        return NarrativePressure(urgency, danger, unresolved, trend, goal_stagnation, 0.0)

    def with_goal_stagnation(self, previous, stagnation):
        """Expose goal friction to planning while preserving unrelated pressure."""
        previous = previous or NarrativePressure()
        value = min(1.0, max(0.0, float(stagnation)))
        urgency = max(previous.urgency, .25 * value)
        unresolved = max(previous.unresolved_degree, .35 * value)
        old_score = (previous.urgency + previous.danger + previous.unresolved_degree) / 3
        new_score = (urgency + previous.danger + unresolved) / 3
        trend = "rising" if new_score > old_score + .01 else previous.trend
        return NarrativePressure(urgency, previous.danger, unresolved, trend, value, previous.conflict_pressure)

    def with_conflict_pressure(self, previous, pressure):
        previous = previous or NarrativePressure()
        value = min(1.0, max(0.0, float(pressure)))
        urgency = max(previous.urgency, .35 * value)
        unresolved = max(previous.unresolved_degree, .5 * value)
        old_score = (previous.urgency + previous.danger + previous.unresolved_degree) / 3
        new_score = (urgency + previous.danger + unresolved) / 3
        trend = "rising" if new_score > old_score + .01 else previous.trend
        return NarrativePressure(urgency, previous.danger, unresolved, trend,
                                 previous.goal_stagnation, value)
