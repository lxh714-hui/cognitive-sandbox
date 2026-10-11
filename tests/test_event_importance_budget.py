from dataclasses import FrozenInstanceError
from itertools import count

import pytest

from cognitive_sandbox.application.event_importance_budget import EventImportanceBudgetPolicy
from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.lazy_expander import LazyExpander
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.story import ExpansionPolicy, StoryBranch


def test_high_importance_gets_larger_expansion_budget():
    policy = EventImportanceBudgetPolicy()

    low = policy.policy_for(0.5)
    high = policy.policy_for(0.7)

    assert high.max_branches_per_expansion > low.max_branches_per_expansion
    assert high.max_total_expansions > low.max_total_expansions


def test_low_importance_gets_smaller_expansion_budget():
    policy = EventImportanceBudgetPolicy()

    low = policy.policy_for(0.3)
    default = policy.policy_for(0.5)

    assert low.max_branches_per_expansion < default.max_branches_per_expansion
    assert low.max_total_expansions < default.max_total_expansions


def test_middle_importance_uses_the_default_policy():
    policy = EventImportanceBudgetPolicy()

    assert policy.policy_for(0.5) == ExpansionPolicy(2, 8)
    assert policy.policy_for(EventImportance(0.5, "medium")) == policy.DEFAULT_BUDGET


@pytest.mark.parametrize(
    ("importance", "expected"),
    [
        (0.0, ExpansionPolicy(1, 3)),
        (0.3, ExpansionPolicy(1, 3)),
        (0.300001, ExpansionPolicy(2, 8)),
        (0.699999, ExpansionPolicy(2, 8)),
        (0.7, ExpansionPolicy(4, 16)),
        (1.0, ExpansionPolicy(4, 16)),
    ],
)
def test_importance_boundaries_map_to_stable_budget_bands(importance, expected):
    assert EventImportanceBudgetPolicy().policy_for(importance) == expected


@pytest.mark.parametrize("importance", [-0.01, 1.01, float("nan"), float("inf")])
def test_importance_outside_unit_interval_is_rejected(importance):
    with pytest.raises(ValueError, match="between 0 and 1"):
        EventImportanceBudgetPolicy().policy_for(importance)


def test_budget_policy_returns_immutable_expansion_policy():
    result = EventImportanceBudgetPolicy().policy_for(0.8)

    with pytest.raises(FrozenInstanceError):
        result.max_total_expansions = 1


def test_importance_budget_controls_existing_lazy_expander():
    ids = count()
    generator = BranchGenerator(branch_id_factory=lambda: f"child-{next(ids)}")
    candidates = tuple(
        ActionCandidate("CONTINUE", (f"target-{index}",), {}) for index in range(5)
    )
    branch = StoryBranch("root", None, "world", 0, None)
    budget_policy = EventImportanceBudgetPolicy()
    expander = LazyExpander(generator)

    low_branches = expander.expand(branch, candidates, budget_policy.policy_for(0.1))
    high_expander = LazyExpander(generator)
    high_branches = high_expander.expand(branch, candidates, budget_policy.policy_for(0.9))

    assert len(low_branches) == 1
    assert len(high_branches) == 4

