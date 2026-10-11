from __future__ import annotations

import math

from cognitive_sandbox.application.event_importance_budget import EventImportanceBudgetPolicy
from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.story import BranchValue, ExpansionPolicy


class AdaptiveExplorationPolicy:
    """Create deterministic expansion budgets from importance and uncertainty."""

    HIGH_IMPORTANCE_THRESHOLD = 0.7
    HIGH_VALUE_THRESHOLD = 0.7
    LOW_VALUE_THRESHOLD = 0.3
    LOW_CONFIDENCE_THRESHOLD = 0.3
    HIGH_CONFIDENCE_THRESHOLD = 0.7

    BRANCHES_PER_EXPANSION_STEP = 1
    TOTAL_EXPANSIONS_STEP = 4

    def __init__(self, base_policy: ExpansionPolicy | None = None) -> None:
        selected = base_policy or EventImportanceBudgetPolicy.DEFAULT_BUDGET
        if not isinstance(selected, ExpansionPolicy):
            raise TypeError("base_policy must be an ExpansionPolicy.")
        self._base_policy = selected

    def policy_for(
        self,
        event_importance: float | EventImportance,
        branch_value: float | BranchValue,
        confidence: float,
    ) -> ExpansionPolicy:
        importance = self._unit_value(event_importance, "event_importance")
        value = self._unit_value(branch_value, "branch_value")
        confidence = self._unit_value(confidence, "confidence")

        branch_adjustment = 0
        total_adjustment = 0

        if importance >= self.HIGH_IMPORTANCE_THRESHOLD:
            branch_adjustment += self.BRANCHES_PER_EXPANSION_STEP
            total_adjustment += self.TOTAL_EXPANSIONS_STEP
        if value >= self.HIGH_VALUE_THRESHOLD and confidence <= self.LOW_CONFIDENCE_THRESHOLD:
            branch_adjustment += self.BRANCHES_PER_EXPANSION_STEP
            total_adjustment += self.TOTAL_EXPANSIONS_STEP
        if value <= self.LOW_VALUE_THRESHOLD and confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            branch_adjustment -= self.BRANCHES_PER_EXPANSION_STEP
            total_adjustment -= self.TOTAL_EXPANSIONS_STEP

        return ExpansionPolicy(
            max_branches_per_expansion=max(
                0, self._base_policy.max_branches_per_expansion + branch_adjustment
            ),
            max_total_expansions=max(
                0, self._base_policy.max_total_expansions + total_adjustment
            ),
        )

    @staticmethod
    def _unit_value(value: float | EventImportance | BranchValue, name: str) -> float:
        if isinstance(value, EventImportance):
            value = value.score
        elif isinstance(value, BranchValue):
            value = value.value
        elif isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number between 0 and 1.")
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1.")
        return value
