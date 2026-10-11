from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_value_evaluator import BranchValueEvaluator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.story import BranchScore, BranchValue, StoryBranch


def _branch(branch_id="branch-1"):
    return StoryBranch(branch_id, "root", "world", 0, None)


def _branch_with_metadata(metadata):
    action = ActionCandidate("CONTINUE", (), metadata)
    return StoryBranch("branch-1", "root", "world", 0, None, action)


def test_branch_value_validates_identity_range_and_immutable_reasons():
    reasons = ["initial rule"]
    value = BranchValue("branch-1", 0.3, reasons)
    reasons.append("later mutation")

    assert value.reasons == ("initial rule",)
    with pytest.raises(ValueError, match="branch_id"):
        BranchValue(" ", 0.3, ())
    with pytest.raises(TypeError, match="collection of strings"):
        BranchValue("branch-1", 0.3, "mutable text")


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf")])
def test_branch_value_rejects_values_outside_unit_interval(value):
    with pytest.raises(ValueError, match="between 0 and 1"):
        BranchValue("branch-1", value, ())


def test_evaluator_uses_neutral_default_when_no_branch_score_exists():
    result = BranchValueEvaluator().evaluate(_branch())

    assert result.branch_id == "branch-1"
    assert result.value == 0.5
    assert result.reasons == ("neutral default value",)


def test_evaluator_adapts_existing_branch_score():
    result = BranchValueEvaluator().evaluate(
        _branch(), BranchScore("branch-1", 0.82, ("existing score",))
    )

    assert result.value == 0.82
    assert result.reasons == ("existing score",)


def test_branch_value_is_frozen_and_evaluator_checks_score_branch():
    result = BranchValueEvaluator().evaluate(_branch())
    with pytest.raises(FrozenInstanceError):
        result.value = 1.0
    with pytest.raises(ValueError, match="belong to the evaluated branch"):
        BranchValueEvaluator().evaluate(_branch(), BranchScore("other", 0.6, ()))


def test_event_importance_changes_value_without_changing_branch_score():
    evaluator = BranchValueEvaluator()
    score = BranchScore("branch-1", 0.5, ("candidate prior",))
    low = evaluator.evaluate(
        _branch_with_metadata({"importance": EventImportance(0.1, "low")}), score
    )
    high = evaluator.evaluate(
        _branch_with_metadata({"importance": EventImportance(0.9, "high")}), score
    )

    assert high.value > low.value
    assert high.value == pytest.approx(0.58)
    assert low.value == pytest.approx(0.42)
    assert high.reasons[0] == "candidate prior"


def test_branch_depth_adds_a_deterministic_penalty():
    evaluator = BranchValueEvaluator()
    score = BranchScore("branch-1", 0.7, ("candidate prior",))
    shallow = evaluator.evaluate(_branch_with_metadata({"depth": 1}), score)
    deep = evaluator.evaluate(_branch_with_metadata({"branch_depth": 3}), score)

    assert shallow.value == pytest.approx(0.65)
    assert deep.value == pytest.approx(0.55)
    assert "branch depth penalty -0.150" in deep.reasons


@pytest.mark.parametrize(
    ("base", "metadata", "expected"),
    [
        (0.95, {"importance": 1.0}, 1.0),
        (0.05, {"importance": 0.0, "depth": 10}, 0.0),
    ],
)
def test_enriched_branch_value_is_clamped_to_unit_interval(base, metadata, expected):
    result = BranchValueEvaluator().evaluate(
        _branch_with_metadata(metadata), BranchScore("branch-1", base, ())
    )

    assert result.value == expected


def test_missing_enrichment_signals_preserve_stable_legacy_values():
    evaluator = BranchValueEvaluator()

    assert evaluator.evaluate(_branch()).value == 0.5
    legacy_score = BranchScore("branch-1", 0.73, ("existing reason",))
    result = evaluator.evaluate(_branch(), legacy_score)
    assert result.value == 0.73
    assert result.reasons == ("existing reason",)
