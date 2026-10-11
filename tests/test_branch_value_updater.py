from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_evaluation_feedback import BranchEvaluationFeedback
from cognitive_sandbox.application.branch_value_updater import BranchValueUpdater
from cognitive_sandbox.domain.story import BranchEvaluationSummary, BranchValue


def test_successful_feedback_can_raise_branch_value():
    updated = BranchValueUpdater().update(
        BranchValue("branch-a", 0.4, ("initial heuristic",)),
        BranchEvaluationFeedback("branch-a", True, 0.8, "Simulation succeeded."),
    )

    assert updated.value == pytest.approx(0.6)
    assert updated.reasons == (
        "initial heuristic",
        "simulation feedback: Simulation succeeded.",
    )


def test_failed_feedback_uses_discounted_feedback_score_and_lowers_value():
    updated = BranchValueUpdater().update(
        BranchValue("branch-a", 0.8, ()),
        BranchEvaluationFeedback("branch-a", False, 0.4, "Simulation failed."),
    )

    assert updated.value == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("old_value", "success", "soft_score", "expected"),
    [
        (0.0, True, 0.0, 0.0),
        (0.0, True, 1.0, 0.5),
        (1.0, True, 1.0, 1.0),
        (1.0, False, 1.0, 0.75),
        (0.0, False, 0.0, 0.0),
    ],
)
def test_feedback_boundaries_keep_updated_value_in_unit_interval(
    old_value, success, soft_score, expected
):
    updated = BranchValueUpdater().update(
        BranchValue("branch-a", old_value, ()),
        BranchEvaluationFeedback("branch-a", success, soft_score, "Boundary result."),
    )

    assert updated.value == pytest.approx(expected)
    assert 0.0 <= updated.value <= 1.0


def test_feedback_model_validates_and_is_immutable():
    feedback = BranchEvaluationFeedback("branch-a", True, 0.7, "ok")
    with pytest.raises(FrozenInstanceError):
        feedback.success = False
    with pytest.raises(ValueError, match="branch_id"):
        BranchEvaluationFeedback(" ", True, 0.7, "ok")
    with pytest.raises(ValueError, match="between 0 and 1"):
        BranchEvaluationFeedback("branch-a", True, 1.1, "ok")


def test_updater_rejects_feedback_for_a_different_branch():
    with pytest.raises(ValueError, match="belong to the branch"):
        BranchValueUpdater().update(
            BranchValue("branch-a", 0.5, ()),
            BranchEvaluationFeedback("branch-b", True, 0.5, "wrong route"),
        )


def test_summary_feedback_updates_branch_value_with_aggregated_formula():
    updated = BranchValueUpdater().update(
        BranchValue("branch-a", 0.4, ("initial heuristic",)),
        BranchEvaluationSummary("branch-a", 4, 3, 0.75, 0.5, 0.4),
    )

    # feedback_score = 0.75 * 0.5 + 0.5 * 0.5 = 0.625
    # weighted = 0.625 * 0.4 + 0.4 * 0.6 = 0.49
    # updated = 0.4 * 0.5 + 0.49 * 0.5 = 0.445
    assert updated.value == pytest.approx(0.445)
    assert "success_rate=0.750" in updated.reasons[-1]


def test_single_feedback_update_remains_supported():
    updated = BranchValueUpdater().update(
        BranchValue("branch-a", 0.4, ()),
        BranchEvaluationFeedback("branch-a", True, 0.8, "single run"),
    )

    assert updated.value == pytest.approx(0.6)


def test_higher_confidence_feedback_has_stronger_effect():
    old_value = BranchValue("branch-a", 0.2, ())
    updater = BranchValueUpdater()
    low_confidence = updater.update(
        old_value,
        BranchEvaluationSummary("branch-a", 1, 1, 1.0, 1.0, 0.1),
    )
    high_confidence = updater.update(
        old_value,
        BranchEvaluationSummary("branch-a", 10, 10, 1.0, 1.0, 1.0),
    )

    assert low_confidence.value == pytest.approx(0.24)
    assert high_confidence.value == pytest.approx(0.6)
    assert high_confidence.value > low_confidence.value


@pytest.mark.parametrize(
    ("old_value", "confidence", "expected"),
    [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.0, 1.0, 0.5), (1.0, 0.0, 1.0)],
)
def test_confidence_aware_update_stays_in_unit_interval(old_value, confidence, expected):
    updated = BranchValueUpdater().update(
        BranchValue("branch-a", old_value, ()),
        BranchEvaluationSummary("branch-a", 1, 1, 1.0, 1.0, confidence),
    )

    assert updated.value == pytest.approx(expected)
    assert 0 <= updated.value <= 1
