from __future__ import annotations

import math

from cognitive_sandbox.domain.story import RolloutAllocation, RolloutPolicy


class RolloutManager:
    """Allocate a bounded, deterministic number of future branch simulations."""

    HIGH_IMPORTANCE_THRESHOLD = 0.7
    LOW_IMPORTANCE_THRESHOLD = 0.3
    HIGH_IMPORTANCE_MULTIPLIER = 1.25
    LOW_IMPORTANCE_MULTIPLIER = 0.75

    def __init__(self, policy: RolloutPolicy) -> None:
        if not isinstance(policy, RolloutPolicy):
            raise TypeError("policy must be a RolloutPolicy.")
        self._policy = policy

    def rollout_count(self, branch_value: float, confidence: float, importance: float) -> int:
        value = self._unit_value(branch_value, "branch_value")
        certainty = self._unit_value(confidence, "confidence")
        event_importance = self._unit_value(importance, "importance")

        exploration_score = value * 0.5 + (1.0 - certainty) * 0.5
        if event_importance >= self.HIGH_IMPORTANCE_THRESHOLD:
            exploration_score *= self.HIGH_IMPORTANCE_MULTIPLIER
        elif event_importance <= self.LOW_IMPORTANCE_THRESHOLD:
            exploration_score *= self.LOW_IMPORTANCE_MULTIPLIER

        span = self._policy.max_rollouts - self._policy.min_rollouts
        count = self._policy.min_rollouts + round(span * exploration_score)
        return min(self._policy.max_rollouts, max(self._policy.min_rollouts, count))

    def allocate(
        self,
        branch_id: str,
        branch_value: float,
        confidence: float,
        importance: float,
    ) -> RolloutAllocation:
        count = self.rollout_count(branch_value, confidence, importance)
        event_importance = self._unit_value(importance, "importance")
        exploration_score = (
            self._unit_value(branch_value, "branch_value") * 0.5
            + (1.0 - self._unit_value(confidence, "confidence")) * 0.5
        )
        if event_importance >= self.HIGH_IMPORTANCE_THRESHOLD:
            tier = "high importance multiplier"
        elif event_importance <= self.LOW_IMPORTANCE_THRESHOLD:
            tier = "low importance multiplier"
        else:
            tier = "default importance"
        return RolloutAllocation(
            branch_id=branch_id,
            rollout_count=count,
            reason=f"exploration_score={exploration_score:.3f}; {tier}",
        )

    @staticmethod
    def _unit_value(value: float, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number between 0 and 1.")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1.")
        return float(value)
