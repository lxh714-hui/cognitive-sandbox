from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.application.branch_evaluation_feedback import BranchEvaluationFeedback
from cognitive_sandbox.domain.story import BranchEvaluationSummary


class BranchEvaluationAggregator:
    """Aggregate repeatable feedback samples belonging to one branch."""

    def aggregate(
        self,
        feedbacks: Iterable[BranchEvaluationFeedback],
    ) -> BranchEvaluationSummary:
        if isinstance(feedbacks, (str, bytes)):
            raise TypeError("feedbacks must contain BranchEvaluationFeedback values.")
        samples = tuple(feedbacks)
        if not samples:
            raise ValueError("At least one branch evaluation feedback is required.")
        if any(not isinstance(item, BranchEvaluationFeedback) for item in samples):
            raise TypeError("feedbacks must contain only BranchEvaluationFeedback values.")
        branch_ids = {item.branch_id for item in samples}
        if len(branch_ids) != 1:
            raise ValueError("All feedbacks must belong to the same branch.")

        success_count = sum(item.success for item in samples)
        sample_count = len(samples)
        return BranchEvaluationSummary(
            branch_id=samples[0].branch_id,
            sample_count=sample_count,
            success_count=success_count,
            success_rate=success_count / sample_count,
            average_soft_score=sum(item.soft_score for item in samples) / sample_count,
            confidence=min(sample_count / 10, 1.0),
        )
