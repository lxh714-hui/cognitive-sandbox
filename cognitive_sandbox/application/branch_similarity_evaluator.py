from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class BranchSemantics:
    goal: str
    method: str
    risk: float
    relationship_change: str
    outcome: str


@runtime_checkable
class BranchSimilarityEvaluator(Protocol):
    """Extension point for future branch convergence decisions."""

    def evaluate(self, left: BranchSemantics, right: BranchSemantics) -> float: ...


class BasicBranchSimilarityEvaluator:
    """Return a comparison score only; this class never merges tree nodes."""

    def evaluate(self, left: BranchSemantics, right: BranchSemantics) -> float:
        if not isinstance(left, BranchSemantics) or not isinstance(right, BranchSemantics):
            raise TypeError("left and right must be BranchSemantics values.")
        if any(not 0 <= item.risk <= 1 for item in (left, right)):
            raise ValueError("risk values must be between 0 and 1.")
        parts = (
            (left.goal, right.goal, .35),
            (left.method, right.method, .2),
            (left.relationship_change, right.relationship_change, .15),
            (left.outcome, right.outcome, .2),
        )
        score = sum(weight for a, b, weight in parts if a.strip().casefold() == b.strip().casefold())
        score += max(0.0, .1 * (1.0 - abs(left.risk - right.risk)))
        return round(min(1.0, score), 4)
