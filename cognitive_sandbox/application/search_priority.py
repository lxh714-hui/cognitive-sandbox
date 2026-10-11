from __future__ import annotations

import math

from cognitive_sandbox.domain.story import BranchValue


class SearchPriorityCalculator:
    """Combine a branch's value with a small uncertainty exploration bonus."""

    EXPLORATION_BONUS = 0.2
    MIN_PRIORITY = 0.0
    MAX_PRIORITY = 1.2

    def calculate(self, branch_value: BranchValue | float, confidence: float) -> float:
        if isinstance(branch_value, BranchValue):
            value = branch_value.value
        else:
            value = branch_value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("branch_value must be a BranchValue or a number between 0 and 1.")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("branch_value must be between 0 and 1.")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise TypeError("confidence must be a number between 0 and 1.")
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")

        priority = float(value) + (1.0 - float(confidence)) * self.EXPLORATION_BONUS
        return min(self.MAX_PRIORITY, max(self.MIN_PRIORITY, priority))
