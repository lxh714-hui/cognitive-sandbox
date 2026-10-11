import math

from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.story import BranchScore, BranchValue, StoryBranch


class BranchValueEvaluator:
    """Combine an action prior with optional static branch metadata signals."""

    IMPORTANCE_BONUS_WEIGHT = 0.2
    DEPTH_PENALTY_WEIGHT = 0.05

    def evaluate(
        self,
        branch: StoryBranch,
        branch_score: BranchScore | None = None,
    ) -> BranchValue:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        if branch_score is not None and not isinstance(branch_score, BranchScore):
            raise TypeError("branch_score must be a BranchScore or None.")
        if branch_score is not None and branch_score.branch_id != branch.branch_id:
            raise ValueError("branch_score must belong to the evaluated branch.")

        metadata = branch.divergence_action.metadata if branch.divergence_action else {}
        base_score = branch_score.score if branch_score is not None else 0.5
        reasons = list(
            branch_score.reasons if branch_score is not None else ("neutral default value",)
        )

        raw_importance = metadata.get("importance")
        if raw_importance is None:
            importance = None
        elif isinstance(raw_importance, EventImportance):
            importance = raw_importance.score
        elif isinstance(raw_importance, bool) or not isinstance(raw_importance, (int, float)):
            raise TypeError("importance metadata must be an EventImportance or a number in [0, 1].")
        else:
            importance = float(raw_importance)
            if not math.isfinite(importance) or not 0 <= importance <= 1:
                raise ValueError("importance metadata must be between 0 and 1.")

        depth = metadata.get("depth", metadata.get("branch_depth", 0))
        if isinstance(depth, bool) or not isinstance(depth, int):
            raise TypeError("branch depth metadata must be a non-negative integer.")
        if depth < 0:
            raise ValueError("branch depth metadata must be non-negative.")

        value = base_score
        if importance is not None:
            bonus = (importance - 0.5) * self.IMPORTANCE_BONUS_WEIGHT
            value += bonus
            reasons.append(f"event importance adjustment {bonus:+.3f}")
        if depth:
            penalty = depth * self.DEPTH_PENALTY_WEIGHT
            value -= penalty
            reasons.append(f"branch depth penalty -{penalty:.3f}")
        value = max(0.0, min(1.0, value))
        return BranchValue(branch.branch_id, value, tuple(reasons))
