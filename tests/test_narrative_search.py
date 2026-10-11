from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.narrative_search import NarrativeSearch
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    BranchScore,
    SearchPolicy,
    SearchStrategy,
    StoryBranch,
)


def _candidate(target, score=None):
    metadata = {} if score is None else {"score": score}
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


def test_search_policy_bounds_depth_nodes_and_per_node_branching():
    result = _search(SearchStrategy.BREADTH_FIRST, max_nodes=2, max_depth=3)
    assert len(result.generated_branches) == 1

    root = StoryBranch("root", None, "world", 0, None)
    service = NarrativeSearch(lambda _branch: (_candidate(str(i)) for i in range(5)))
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
