from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import BranchGenerationResult, StoryBranch


def _candidate(action_type, target):
    return ActionCandidate(action_type, (target,), {"decision": "candidate"})


def test_branch_generator_creates_one_child_route_per_candidate():
    source = StoryBranch("main", None, "harbor", 7, None)
    candidates = (_candidate("INSPECT_OBJECT", "cup"), _candidate("LEAVE_ROOM", "kitchen"))
    ids = iter(("branch-a", "branch-b"))
    generator = BranchGenerator(
        branch_id_factory=lambda: next(ids),
        generation_id_factory=lambda: "generation-1",
    )

    branches, result = generator.generate_with_result(
        source,
        candidates,
        divergence_event_id="event-7",
    )

    assert [branch.branch_id for branch in branches] == ["branch-a", "branch-b"]
    assert all(branch.parent_branch_id == "main" for branch in branches)
    assert all(branch.world_id == "harbor" and branch.revision == 7 for branch in branches)
    assert all(branch.divergence_event_id == "event-7" for branch in branches)
    assert [branch.divergence_action for branch in branches] == list(candidates)
    assert result == BranchGenerationResult(
        "generation-1", "main", ("branch-a", "branch-b")
    )


def test_branch_generator_handles_no_candidates_without_creating_routes():
    source = StoryBranch("main", None, "harbor", 0, None)

    branches, result = BranchGenerator(
        generation_id_factory=lambda: "generation-empty"
    ).generate_with_result(source, ())

    assert branches == ()
    assert result.created_branches == ()


def test_branch_generation_result_is_immutable_and_validates_branch_ids():
    result = BranchGenerationResult("gen", "main", ("route-a",))

    with pytest.raises(FrozenInstanceError):
        result.generation_id = "changed"
    with pytest.raises(ValueError, match="source branch"):
        BranchGenerationResult("gen", "main", ("main",))
    with pytest.raises(ValueError, match="unique"):
        BranchGenerationResult("gen", "main", ("route-a", "route-a"))


def test_branch_generator_rejects_invalid_candidate_input():
    source = StoryBranch("main", None, "harbor", 0, None)
    generator = BranchGenerator()

    with pytest.raises(TypeError, match="ActionCandidate"):
        generator.generate(source, [object()])
    with pytest.raises(ValueError, match="divergence_event_id"):
        generator.generate(source, [], divergence_event_id=" ")
