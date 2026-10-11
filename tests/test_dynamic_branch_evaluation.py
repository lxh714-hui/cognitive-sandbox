from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.dynamic_branch_evaluator import DynamicBranchEvaluator
from cognitive_sandbox.application.narrative_search import NarrativeSearch
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    DynamicBranchScore,
    SearchPolicy,
    SearchStrategy,
    StoryBranch,
    StorySimulationResult,
    ConstraintEvaluation,
)
from cognitive_sandbox.domain.world_events import WorldEvent


def _simulation(branch_id, *, accepted=True, soft_score=0.5, simulation_id=None):
    event = WorldEvent(
        event_id=f"event-{branch_id}",
        branch_id=branch_id,
        world_id="world",
        event_type="ACTION_RESOLVED",
        actor_id="agent",
        payload={},
        world_revision=1,
    )
    evaluation = ConstraintEvaluation(
        event.event_id,
        accepted,
        () if accepted else ("hard-rule",),
        soft_score,
        (),
    )
    return StorySimulationResult(simulation_id or f"sim-{branch_id}", accepted, 1, (event,), evaluation)


def test_dynamic_evaluator_scores_simulation_and_zeroes_hard_constraint_failure():
    branch = StoryBranch("route-a", "root", "world", 1, "event-root")
    passing = DynamicBranchEvaluator(
        lambda _branch: _simulation("route-a", soft_score=0.75)
    ).evaluate(branch)
    failing = DynamicBranchEvaluator(
        lambda _branch: _simulation("route-a", accepted=False, soft_score=0.95)
    ).evaluate(branch)

    assert passing == DynamicBranchScore("route-a", "sim-route-a", True, 0.75, 0.75)
    assert failing.hard_passed is False
    assert failing.soft_score == 0.95
    assert failing.final_score == 0.0


def test_dynamic_evaluator_requires_simulation_events_for_the_branch():
    branch = StoryBranch("route-a", "root", "world", 1, None)
    evaluator = DynamicBranchEvaluator(lambda _branch: _simulation("other"))
    with pytest.raises(ValueError, match="belong to the evaluated branch"):
        evaluator.evaluate(branch)


def test_dynamic_scores_guide_narrative_search_using_simulation_outcomes():
    root = StoryBranch("root", None, "world", 0, None)

    def candidates(branch):
        if branch.branch_id == "root":
            return (
                ActionCandidate("CONTINUE", ("A",), {"score": 0.99}),
                ActionCandidate("CONTINUE", ("B",), {"score": 0.01}),
            )
        return (ActionCandidate("CONTINUE", (f"next-{branch.branch_id}",), {}),)

    dynamic_scorer = DynamicBranchEvaluator(
        lambda branch: _simulation(
            branch.branch_id,
            soft_score={"A": 0.1, "B": 0.8}.get(branch.branch_id, 0.6),
        )
    )
    branch_ids = iter(("A", "B", "child-B"))
    search = NarrativeSearch(
        candidates,
        branch_generator=BranchGenerator(branch_id_factory=lambda: next(branch_ids)),
        branch_scorer=dynamic_scorer,
    )

    result = search.search(
        root,
        SearchPolicy(SearchStrategy.SCORE_GUIDED, max_depth=2, max_nodes=4, max_branches_per_node=2),
    )

    assert result.expanded_branch_ids == ("root", "B")
    assert result.best_branch_id == "B"
    assert {score.branch_id: score.final_score for score in dynamic_scorer.dynamic_scores} == {
        "A": 0.1,
        "B": 0.8,
        "child-B": 0.6,
    }
    assert {score.branch_id: score.score for score in result.branch_scores} == {
        "A": 0.1,
        "B": 0.8,
        "child-B": 0.6,
    }


def test_dynamic_score_is_immutable_and_validates_final_score():
    score = DynamicBranchScore("branch", "simulation", True, 0.6, 0.6)
    with pytest.raises(FrozenInstanceError):
        score.final_score = 0.2
    with pytest.raises(ValueError, match="final_score"):
        DynamicBranchScore("branch", "simulation", False, 0.6, 0.6)
