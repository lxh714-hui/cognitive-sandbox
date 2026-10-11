from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BranchEvaluationFeedback:
    branch_id: str
    success: bool
    soft_score: float
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        if not isinstance(self.success, bool):
            raise TypeError("success must be a boolean.")
        if isinstance(self.soft_score, bool) or not isinstance(self.soft_score, (int, float)):
            raise TypeError("soft_score must be a number between 0 and 1.")
        if not math.isfinite(self.soft_score) or not 0 <= self.soft_score <= 1:
            raise ValueError("soft_score must be between 0 and 1.")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty.")
        object.__setattr__(self, "soft_score", float(self.soft_score))
