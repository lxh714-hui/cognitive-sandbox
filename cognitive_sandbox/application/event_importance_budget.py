from __future__ import annotations

import math

from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.story import ExpansionPolicy


class EventImportanceBudgetPolicy:
    """Map event importance bands to deterministic branch expansion budgets."""

    LOW_IMPORTANCE_MAX = 0.3
    HIGH_IMPORTANCE_MIN = 0.7

    LOW_BUDGET = ExpansionPolicy(max_branches_per_expansion=1, max_total_expansions=3)
    DEFAULT_BUDGET = ExpansionPolicy(max_branches_per_expansion=2, max_total_expansions=8)
    HIGH_BUDGET = ExpansionPolicy(max_branches_per_expansion=4, max_total_expansions=16)

    def policy_for(self, event_importance: float | EventImportance) -> ExpansionPolicy:
        if isinstance(event_importance, EventImportance):
            importance = event_importance.score
        elif isinstance(event_importance, bool) or not isinstance(event_importance, (int, float)):
            raise TypeError("event_importance must be a number or EventImportance.")
        else:
            importance = float(event_importance)

        if not math.isfinite(importance) or not 0 <= importance <= 1:
            raise ValueError("event_importance must be between 0 and 1.")
        if importance <= self.LOW_IMPORTANCE_MAX:
            return self.LOW_BUDGET
        if importance >= self.HIGH_IMPORTANCE_MIN:
            return self.HIGH_BUDGET
        return self.DEFAULT_BUDGET
