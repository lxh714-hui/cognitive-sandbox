from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.narrative_search import NarrativeSearch
from cognitive_sandbox.application.branch_value_evaluator import BranchValueEvaluator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    BranchScore,
    BranchValue,
    SearchPolicy,
    SearchStrategy,
    StoryBranch,
)


def _candidate(target, score=None, confidence=None):
    metadata = {} if score is None else {"score": score}
    if confidence is not None:
        metadata["confidence"] = confidence
    return ActionCandidate("CONTINUE", (target,), metadata)


def _search(strategy, *, max_nodes=4, max_depth=4, max_branches=2):
    root = StoryBranch("root", None, "world", 0, None)

    def candidates(branch):
        if branch.branch_id == "root":
            return (_candidate("A", 0.2), _candidate("B", 0.9))
        return (_candidate(f"next-{branch.branch_id}", 0.5),)

    ids = iter(("A", "B", "child-1", "child-2"))
    service = NarrativeSearch(
        candidates,
        branch_value_evaluator=BranchValueEvaluator(),
        branch_generator=BranchGenerator(branch_id_factory=lambda: next(ids)),
        search_id_factory=lambda: "search-1",
    )
    return service.search(root, SearchPolicy(strategy, max_depth, max_nodes, max_branches))


def test_search_strategy_selects_breadth_depth_and_score_guided_routes():
    breadth = _search(SearchStrategy.BREADTH_FIRST)
    depth = _search(SearchStrategy.DEPTH_FIRST)
    guided = _search(SearchStrategy.SCORE_GUIDED)

    assert breadth.expanded_branch_ids == ("root", "A")
    assert depth.expanded_branch_ids == ("root", "B")
    assert guided.expanded_branch_ids == ("root", "B")
    assert breadth.generated_branches[-1].parent_branch_id == "A"
    assert depth.generated_branches[-1].parent_branch_id == "B"
    assert guided.generated_branches[-1].parent_branch_id == "B"
    assert guided.best_branch_id == "B"
    assert guided.search_id == "search-1"
    assert {score.branch_id: score.score for score in guided.branch_scores} == {
        "A": 0.2,
        "B": 0.9,
        "child-1": 0.5,
    }
    assert {value.branch_id: value.value for value in guided.branch_values} == {
        "A": 0.2,
        "B": 0.9,
        "child-1": 0.5,
    }


def test_search_policy_bounds_depth_nodes_and_per_node_branching():
    result = _search(SearchStrategy.BREADTH_FIRST, max_nodes=2, max_depth=3)
    assert len(result.generated_branches) == 1

    root = StoryBranch("root", None, "world", 0, None)
    service = NarrativeSearch(
        lambda _branch: (_candidate(str(i)) for i in range(5)),
        branch_value_evaluator=BranchValueEvaluator(),
    )
    bounded = service.search(root, SearchPolicy(SearchStrategy.BREADTH_FIRST, 1, 10, 2))
    assert len(bounded.generated_branches) == 2
    assert bounded.depth_reached == 1

    depth_zero = service.search(root, SearchPolicy(SearchStrategy.DEPTH_FIRST, 0, 10, 2))
    assert depth_zero.generated_branches == ()
    assert depth_zero.expanded_branch_ids == ()


def test_search_policy_and_branch_scores_validate_and_are_immutable():
    with pytest.raises(TypeError):
        SearchPolicy("breadth_first", 1, 2, 1)
    with pytest.raises(ValueError, match="max_nodes"):
        SearchPolicy(SearchStrategy.BREADTH_FIRST, 1, 0, 1)
    with pytest.raises(ValueError, match="max_depth"):
        SearchPolicy(SearchStrategy.DEPTH_FIRST, -1, 2, 1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        BranchScore("branch", 1.2, ("bad score",))

    result = _search(SearchStrategy.SCORE_GUIDED)
    with pytest.raises(FrozenInstanceError):
        result.depth_reached = 10


def test_score_guided_search_uses_injected_branch_values_and_retains_branch_scores():
    class PreferLowerScoreEvaluator(BranchValueEvaluator):
        def __init__(self):
            self.evaluated = []

        def evaluate(self, branch, branch_score=None):
            self.evaluated.append((branch.branch_id, branch_score))
            evaluated = super().evaluate(branch, branch_score)
            preference = {"A": 0.9, "B": 0.1}.get(branch.branch_id, evaluated.value)
            return BranchValue(branch.branch_id, preference, ("injected preference",))

    root = StoryBranch("root", None, "world", 0, None)
    evaluator = PreferLowerScoreEvaluator()
    ids = iter(("A", "B", "child-A"))
    search = NarrativeSearch(
        lambda branch: (
            (_candidate("a", 0.2), _candidate("b", 0.9))
            if branch.branch_id == "root"
            else (_candidate("next", 0.5),)
        ),
        branch_value_evaluator=evaluator,
        branch_generator=BranchGenerator(branch_id_factory=lambda: next(ids)),
    )

    result = search.search(root, SearchPolicy(SearchStrategy.SCORE_GUIDED, 2, 4, 2))

    assert result.expanded_branch_ids == ("root", "A")
    assert result.best_branch_id == "A"
    assert [branch_id for branch_id, _score in evaluator.evaluated] == ["A", "B", "child-A"]
    assert {score.branch_id: score.score for score in result.branch_scores} == {
        "A": 0.2,
        "B": 0.9,
        "child-A": 0.5,
    }
    assert {value.branch_id: value.value for value in result.branch_values} == {
        "A": 0.9,
        "B": 0.1,
        "child-A": 0.5,
    }


def test_score_guided_search_uses_confidence_priority_while_bfs_dfs_order_stays_same():
    root = StoryBranch("root", None, "world", 0, None)

    def candidates(branch):
        if branch.branch_id == "root":
            return (
                _candidate("a", 0.75, confidence=0.2),
                _candidate("b", 0.85, confidence=1.0),
            )
        return (_candidate(f"next-{branch.branch_id}", 0.5),)

    def run(strategy):
        ids = iter(("A", "B", "child-A", "child-B"))
        search = NarrativeSearch(
            candidates,
            branch_value_evaluator=BranchValueEvaluator(),
            branch_generator=BranchGenerator(branch_id_factory=lambda: next(ids)),
        )
        return search.search(root, SearchPolicy(strategy, 2, 4, 2))

    guided = run(SearchStrategy.SCORE_GUIDED)
    breadth = run(SearchStrategy.BREADTH_FIRST)
    depth = run(SearchStrategy.DEPTH_FIRST)

    assert guided.expanded_branch_ids == ("root", "A")
    assert guided.best_branch_id == "A"
    assert breadth.expanded_branch_ids == ("root", "A")
    assert depth.expanded_branch_ids == ("root", "B")
