from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.lazy_expander import LazyExpander
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import ExpansionPolicy, StoryBranch


def _branch():
    return StoryBranch("root", None, "world", 0, None)


def _candidate(name):
    return ActionCandidate("CONTINUE", (name,), {})


def test_lazy_expander_limits_per_expansion_and_preserves_candidate_order():
    candidates = [_candidate(name) for name in "ABCDE"]
    original = list(candidates)
    ids = iter(("child-a", "child-b", "child-c"))
    expander = LazyExpander(BranchGenerator(branch_id_factory=lambda: next(ids)))

    children = expander.expand(_branch(), candidates, ExpansionPolicy(3, 10))

    assert [child.divergence_action.target_refs[0] for child in children] == ["A", "B", "C"]
    assert candidates == original
    assert expander.total_expansions == 3


def test_empty_candidates_produce_no_branches_or_budget_use():
    expander = LazyExpander()

    assert expander.expand(_branch(), (), ExpansionPolicy(3, 5)) == ()
    assert expander.total_expansions == 0


def test_total_expansion_budget_is_shared_across_calls():
    ids = iter(("child-a", "child-b", "child-c"))
    expander = LazyExpander(BranchGenerator(branch_id_factory=lambda: next(ids)))
    candidates = [_candidate(name) for name in "ABCDE"]
    policy = ExpansionPolicy(max_branches_per_expansion=3, max_total_expansions=3)

    first = expander.expand(_branch(), candidates, policy)
    second = expander.expand(_branch(), candidates, policy)

    assert len(first) == 3
    assert second == ()
    assert expander.total_expansions == 3


def test_per_expansion_limit_and_total_remaining_limit_are_both_applied():
    ids = iter(("child-a", "child-b", "child-c"))
    expander = LazyExpander(BranchGenerator(branch_id_factory=lambda: next(ids)))
    candidates = [_candidate(name) for name in "ABCDE"]

    first = expander.expand(_branch(), candidates, ExpansionPolicy(2, 3))
    second = expander.expand(_branch(), candidates, ExpansionPolicy(2, 3))

    assert len(first) == 2
    assert [item.divergence_action.target_refs[0] for item in second] == ["A"]
    assert expander.total_expansions == 3


def test_expansion_policy_validates_non_negative_limits_and_is_immutable():
    policy = ExpansionPolicy(0, 0)
    with pytest.raises(FrozenInstanceError):
        policy.max_total_expansions = 4
    with pytest.raises(ValueError, match="max_branches_per_expansion"):
        ExpansionPolicy(-1, 2)
    with pytest.raises(ValueError, match="max_total_expansions"):
        ExpansionPolicy(1, -1)
    with pytest.raises(TypeError, match="non-negative integer"):
        ExpansionPolicy(True, 2)


def test_zero_expansion_policy_returns_no_children():
    expander = LazyExpander()
    assert expander.expand(_branch(), [_candidate("A")], ExpansionPolicy(0, 4)) == ()
    assert expander.expand(_branch(), [_candidate("A")], ExpansionPolicy(4, 0)) == ()
