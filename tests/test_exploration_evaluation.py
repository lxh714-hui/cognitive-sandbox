from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.exploration_evaluator import ExplorationEvaluator
from cognitive_sandbox.domain.story import (
    BranchExplorationResult,
    ConstraintEvaluation,
    ExplorationEvaluation,
    StoryBranch,
    StorySimulationResult,
)
from cognitive_sandbox.domain.world_events import WorldEvent


def _branch(branch_id):
    return StoryBranch(branch_id, "root", "world", 1, f"event-{branch_id}")


def _exploration(*branch_ids):
    branches = tuple(_branch(branch_id) for branch_id in branch_ids)
    return BranchExplorationResult(
        "exploration-1", "root", branches, (1,) * len(branches), ("root",), 1 if branches else 0
    )


def _simulation(simulation_id, branch_id, *, success, accepted=True, soft_score=0.5):
    evaluation = ConstraintEvaluation(
        world_event_id=f"event-{simulation_id}",
        accepted=accepted,
        hard_violations=() if accepted else ("hard-rule",),
        soft_score=soft_score,
        matched_soft_constraints=(),
    )
    event = WorldEvent(
        event_id=f"event-{simulation_id}",
        branch_id=branch_id,
        world_id="world",
        event_type="TEST_EVENT",
        actor_id="agent",
        payload={},
        world_revision=1,
    )
    return StorySimulationResult(simulation_id, success, 1, (event,), evaluation)


def test_evaluator_aggregates_success_soft_scores_and_selects_best_branch():
    evaluator = ExplorationEvaluator(evaluation_id_factory=lambda: "evaluation-1")

    result = evaluator.evaluate(
        (_exploration("branch-a", "branch-b", "branch-c"),),
        (
            _simulation("sim-a", "branch-a", success=True, soft_score=0.6),
            _simulation("sim-b", "branch-b", success=True, soft_score=0.9),
            _simulation("sim-c", "branch-c", success=False, soft_score=1.0),
        ),
    )

    assert result.evaluation_id == "evaluation-1"
    assert result.explored_count == 3
    assert result.successful_branches == ("branch-a", "branch-b")
    assert result.best_branch_id == "branch-b"
    assert result.average_soft_score == pytest.approx(0.8333333333)


def test_evaluator_uses_constraint_acceptance_and_deterministic_tie_break():
    result = ExplorationEvaluator().evaluate(
        (_exploration("branch-z", "branch-a", "branch-rejected"),),
        (
            _simulation("sim-z", "branch-z", success=True, soft_score=0.8),
            _simulation("sim-a", "branch-a", success=True, soft_score=0.8),
            _simulation(
                "sim-rejected", "branch-rejected", success=True, accepted=False, soft_score=1.0
            ),
        ),
    )

    assert result.best_branch_id == "branch-a"


def test_evaluator_ignores_unattributable_and_unexplored_simulations():
    exploration = _exploration("branch-a")
    unattributable = StorySimulationResult(
        "empty", True, 0, (), ConstraintEvaluation("empty-event", True, (), 1.0, ())
    )
    result = ExplorationEvaluator().evaluate(
        (exploration,),
        (
            unattributable,
            _simulation("other", "not-explored", success=True, soft_score=1.0),
        ),
    )

    assert result.explored_count == 1
    assert result.successful_branches == ()
    assert result.best_branch_id is None
    assert result.average_soft_score == 0.0


def test_evaluator_rejects_invalid_and_duplicate_inputs():
    evaluator = ExplorationEvaluator()
    with pytest.raises(TypeError, match="only BranchExplorationResult"):
        evaluator.evaluate((object(),), ())
    with pytest.raises(TypeError, match="only StorySimulationResult"):
        evaluator.evaluate((), (object(),))
    with pytest.raises(ValueError, match="repeat branch IDs"):
        evaluator.evaluate((_exploration("same"), _exploration("same")), ())


def test_exploration_evaluation_validates_and_is_immutable():
    result = ExplorationEvaluation("evaluation", 1, ("branch-a",), "branch-a", 0.4)
    with pytest.raises(FrozenInstanceError):
        result.best_branch_id = None
    with pytest.raises(ValueError, match="cannot exceed"):
        ExplorationEvaluation("evaluation", 0, ("branch-a",), None, 0.0)
    with pytest.raises(ValueError, match="between 0 and 1"):
        ExplorationEvaluation("evaluation", 1, (), None, 1.1)
