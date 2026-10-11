import pytest

from cognitive_sandbox.application.adaptive_exploration_policy import AdaptiveExplorationPolicy
from cognitive_sandbox.application.event_importance_budget import EventImportanceBudgetPolicy
from cognitive_sandbox.domain.simulation import EventImportance
from cognitive_sandbox.domain.story import BranchValue, ExpansionPolicy


def test_high_importance_increases_expansion_budget():
    baseline = EventImportanceBudgetPolicy.DEFAULT_BUDGET
    result = AdaptiveExplorationPolicy().policy_for(0.8, 0.5, 0.5)

    assert result.max_branches_per_expansion > baseline.max_branches_per_expansion
    assert result.max_total_expansions > baseline.max_total_expansions


def test_high_value_with_low_confidence_increases_budget():
    baseline = EventImportanceBudgetPolicy.DEFAULT_BUDGET
    result = AdaptiveExplorationPolicy().policy_for(0.5, 0.9, 0.2)

    assert result.max_branches_per_expansion > baseline.max_branches_per_expansion
    assert result.max_total_expansions > baseline.max_total_expansions


def test_low_value_with_high_confidence_reduces_budget():
    baseline = EventImportanceBudgetPolicy.DEFAULT_BUDGET
    result = AdaptiveExplorationPolicy().policy_for(0.5, 0.1, 0.8)

    assert result.max_branches_per_expansion < baseline.max_branches_per_expansion
    assert result.max_total_expansions < baseline.max_total_expansions


def test_boundary_inputs_and_importance_value_models_are_supported():
    policy = AdaptiveExplorationPolicy()

    low = policy.policy_for(EventImportance(0.0, "low"), BranchValue("b", 0.0, ()), 1.0)
    high = policy.policy_for(EventImportance(1.0, "high"), BranchValue("b", 1.0, ()), 0.0)

    assert isinstance(low, ExpansionPolicy)
    assert isinstance(high, ExpansionPolicy)
    assert low.max_branches_per_expansion >= 0
    assert low.max_total_expansions >= 0
    assert high.max_branches_per_expansion >= 0
    assert high.max_total_expansions >= 0
    assert high.max_branches_per_expansion > low.max_branches_per_expansion
    assert high.max_total_expansions > low.max_total_expansions


@pytest.mark.parametrize(
    "inputs",
    [(-0.1, 0.5, 0.5), (0.5, 1.1, 0.5), (0.5, 0.5, -0.1), (0.5, 0.5, float("nan"))],
)
def test_policy_rejects_out_of_range_signals(inputs):
    with pytest.raises(ValueError):
        AdaptiveExplorationPolicy().policy_for(*inputs)


def test_custom_base_policy_is_preserved_without_adjustment():
    custom = ExpansionPolicy(3, 11)
    result = AdaptiveExplorationPolicy(custom).policy_for(0.5, 0.5, 0.5)

    assert result == custom
