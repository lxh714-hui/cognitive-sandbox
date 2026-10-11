from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_evaluation_aggregator import (
    BranchEvaluationAggregator,
)
from cognitive_sandbox.application.branch_evaluation_feedback import BranchEvaluationFeedback
from cognitive_sandbox.domain.story import BranchEvaluationSummary


def test_aggregator_calculates_success_rate_and_average_soft_score():
    summary = BranchEvaluationAggregator().aggregate(
        (
            BranchEvaluationFeedback("branch-a", True, 0.8, "success"),
            BranchEvaluationFeedback("branch-a", False, 0.4, "failure"),
            BranchEvaluationFeedback("branch-a", True, 0.6, "success"),
        )
    )

    assert summary.branch_id == "branch-a"
    assert summary.sample_count == 3
    assert summary.success_count == 2
    assert summary.success_rate == pytest.approx(2 / 3)
    assert summary.average_soft_score == pytest.approx(0.6)
    assert summary.confidence == pytest.approx(0.3)


def test_aggregator_rejects_empty_or_mixed_branch_inputs():
    aggregator = BranchEvaluationAggregator()
    with pytest.raises(ValueError, match="At least one"):
        aggregator.aggregate(())
    with pytest.raises(ValueError, match="same branch"):
        aggregator.aggregate(
            (
                BranchEvaluationFeedback("branch-a", True, 0.8, "success"),
                BranchEvaluationFeedback("branch-b", False, 0.2, "failure"),
            )
        )


def test_summary_model_is_immutable_and_validates_counts_and_rates():
    summary = BranchEvaluationSummary("branch-a", 2, 1, 0.5, 0.7, 0.2)
    with pytest.raises(FrozenInstanceError):
        summary.success_rate = 1.0
    with pytest.raises(ValueError, match="must not exceed"):
        BranchEvaluationSummary("branch-a", 1, 2, 1.0, 0.5, 0.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        BranchEvaluationSummary("branch-a", 1, 1, 1.1, 0.5, 0.1)
    with pytest.raises(ValueError, match="confidence"):
        BranchEvaluationSummary("branch-a", 1, 1, 1.0, 0.5, 1.1)


def test_empty_summary_is_a_valid_zero_summary():
    assert BranchEvaluationSummary("branch-a", 0, 0, 0.0, 0.0, 0.0) == BranchEvaluationSummary(
        "branch-a", 0, 0, 0.0, 0.0, 0.0
    )


@pytest.mark.parametrize(("sample_count", "expected"), [(0, 0.0), (1, 0.1), (5, 0.5), (10, 1.0), (15, 1.0)])
def test_aggregator_confidence_uses_sample_count_boundaries(sample_count, expected):
    feedbacks = tuple(
        BranchEvaluationFeedback("branch-a", index % 2 == 0, 0.4, "sample")
        for index in range(sample_count)
    )
    if sample_count == 0:
        with pytest.raises(ValueError, match="At least one"):
            BranchEvaluationAggregator().aggregate(feedbacks)
        return

    summary = BranchEvaluationAggregator().aggregate(feedbacks)
    assert summary.confidence == pytest.approx(expected)
