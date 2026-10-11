from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_comparison import BranchComparisonService
from cognitive_sandbox.domain.story import (
    BranchComparisonResult,
    ConstraintEvaluation,
    StorySimulationResult,
)


def _result(simulation_id, *, success, accepted=True, soft_score=0.5):
    evaluation = ConstraintEvaluation(
        world_event_id=f"event-{simulation_id}",
        accepted=accepted,
        hard_violations=() if accepted else ("hard-constraint",),
        soft_score=soft_score,
        matched_soft_constraints=(),
    )
    return StorySimulationResult(simulation_id, success, 2, (), evaluation)


def test_branch_comparison_ranks_success_and_constraint_quality_deterministically():
    results = [
        _result("sim-c", success=True, accepted=True, soft_score=0.7),
        _result("sim-b", success=True, accepted=True, soft_score=0.9),
        _result("sim-a", success=False, accepted=False, soft_score=1.0),
        _result("sim-d", success=True, accepted=False, soft_score=1.0),
    ]

    comparison = BranchComparisonService(
        comparison_id_factory=lambda: "comparison-1"
    ).compare(results)

    assert comparison.comparison_id == "comparison-1"
    assert comparison.simulation_ids == ("sim-c", "sim-b", "sim-a", "sim-d")
    assert comparison.ranking == ("sim-b", "sim-c", "sim-d", "sim-a")
    assert comparison.successful_simulations == ("sim-b", "sim-c", "sim-d")


def test_branch_comparison_uses_simulation_id_for_final_ties():
    results = [
        _result("sim-z", success=True, soft_score=0.5),
        _result("sim-a", success=True, soft_score=0.5),
    ]

    result = BranchComparisonService().compare(results)

    assert result.ranking == ("sim-a", "sim-z")


def test_branch_comparison_requires_nonempty_unique_valid_results():
    service = BranchComparisonService()

    with pytest.raises(ValueError, match="At least one"):
        service.compare([])
    with pytest.raises(TypeError, match="only StorySimulationResult"):
        service.compare([object()])
    duplicate = _result("same", success=True)
    with pytest.raises(ValueError, match="unique"):
        service.compare([duplicate, duplicate])


def test_comparison_result_is_immutable_and_checks_membership():
    result = BranchComparisonResult("cmp", ("a", "b"), ("a",), ("a", "b"))

    with pytest.raises(FrozenInstanceError):
        result.ranking = ("b", "a")
    with pytest.raises(ValueError, match="each simulation ID"):
        BranchComparisonResult("cmp", ("a", "b"), (), ("a", "a"))
