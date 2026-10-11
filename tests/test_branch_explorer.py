from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_explorer import BranchExplorer
from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import BranchExplorationConfig, BranchExplorationResult, StoryBranch


def _candidate(target):
    return ActionCandidate("INSPECT_OBJECT", (target,), {})


def test_explorer_expands_candidate_routes_to_limited_depth():
    root = StoryBranch("root", None, "harbor", 4, "event-root")
    choices = {
        "root": [_candidate("cup-a"), _candidate("cup-b")],
        "child-a": [_candidate("clue-a")],
        "child-b": [_candidate("clue-b")],
    }
    branch_ids = iter(("child-a", "child-b", "leaf-a", "leaf-b"))
    explorer = BranchExplorer(
        lambda branch: choices.get(branch.branch_id, []),
        branch_generator=BranchGenerator(branch_id_factory=lambda: next(branch_ids)),
        exploration_id_factory=lambda: "explore-1",
    )

    result = explorer.explore(root, BranchExplorationConfig(max_depth=2, max_branches_per_node=2))

    assert result.exploration_id == "explore-1"
    assert result.root_branch_id == "root"
    assert [branch.branch_id for branch in result.generated_branches] == [
        "child-a", "child-b", "leaf-a", "leaf-b"
    ]
    assert result.branch_depths == (1, 1, 2, 2)
    assert result.expanded_branch_ids == ("root", "child-a", "child-b")
    assert result.depth_reached == 2
    assert all(branch.divergence_action is not None for branch in result.generated_branches)


def test_explorer_applies_per_node_branch_cap():
    root = StoryBranch("root", None, "harbor", 0, None)
    branch_ids = iter(("child-1", "child-2"))
    explorer = BranchExplorer(
        lambda _branch: [_candidate("a"), _candidate("b"), _candidate("c")],
        branch_generator=BranchGenerator(branch_id_factory=lambda: next(branch_ids)),
    )

    result = explorer.explore(root, BranchExplorationConfig(1, 2))

    assert [branch.branch_id for branch in result.generated_branches] == ["child-1", "child-2"]
    assert result.depth_reached == 1


def test_explorer_depth_zero_and_no_candidates_generate_no_branches():
    root = StoryBranch("root", None, "harbor", 0, None)
    explorer = BranchExplorer(lambda _branch: [_candidate("ignored")])

    result = explorer.explore(root, BranchExplorationConfig(0, 3))

    assert result.generated_branches == ()
    assert result.expanded_branch_ids == ()
    assert result.depth_reached == 0

    empty = BranchExplorer(lambda _branch: []).explore(root, BranchExplorationConfig(3, 2))
    assert empty.generated_branches == ()
    assert empty.expanded_branch_ids == ("root",)


def test_exploration_config_validates_limits():
    with pytest.raises(ValueError, match="max_depth"):
        BranchExplorationConfig(-1, 2)
    with pytest.raises(ValueError, match="max_branches_per_node"):
        BranchExplorationConfig(1, 0)
    with pytest.raises(TypeError):
        BranchExplorationConfig(True, 2)


def test_exploration_result_is_immutable_and_checks_depth_alignment():
    root = StoryBranch("root", None, "harbor", 0, None)
    result = BranchExplorationResult("exp", "root", (), (), (), 0)

    with pytest.raises(FrozenInstanceError):
        result.depth_reached = 1
    with pytest.raises(ValueError, match="align"):
        BranchExplorationResult("exp", "root", (root,), (), (), 0)
