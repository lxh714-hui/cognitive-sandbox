from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.adaptive_exploration_policy import AdaptiveExplorationPolicy
from cognitive_sandbox.application.branch_pruner import BranchPruner
from cognitive_sandbox.application.exploration_controller import ExplorationController
from cognitive_sandbox.application.rollout_manager import RolloutManager
from cognitive_sandbox.application.search_priority import SearchPriorityCalculator
from cognitive_sandbox.domain.story import (
    BranchValue,
    ConstraintCheck,
    ExpansionPolicy,
    ExplorationPlan,
    PruningDecision,
    PruningPolicy,
    RoleStateCheck,
    RolloutAllocation,
    RolloutPolicy,
    StoryBranch,
)


def make_controller(*, minimum_value=0.0, priority_calculator=None, adaptive_policy=None, rollout_manager=None):
    return ExplorationController(
        branch_pruner=BranchPruner(),
        priority_calculator=priority_calculator or SearchPriorityCalculator(),
        adaptive_exploration_policy=adaptive_policy or AdaptiveExplorationPolicy(),
        rollout_manager=rollout_manager or RolloutManager(RolloutPolicy(1, 10)),
        pruning_policy=PruningPolicy(minimum_value),
    )


def test_pruned_branch_returns_non_exploration_plan_without_downstream_calls():
    class MustNotCall:
        def calculate(self, *_args):
            raise AssertionError("priority should not be calculated for a pruned branch")

        def policy_for(self, *_args):
            raise AssertionError("expansion budget should not be calculated for a pruned branch")

        def allocate(self, *_args):
            raise AssertionError("rollouts should not be allocated for a pruned branch")

    controller = make_controller(
        minimum_value=0.5,
        priority_calculator=MustNotCall(),
        adaptive_policy=MustNotCall(),
        rollout_manager=MustNotCall(),
    )
    branch = StoryBranch("branch-1", None, "world", 0, None)

    plan = controller.plan(branch, BranchValue("branch-1", 0.2, ()), 0.5, 0.5)

    assert not plan.should_explore
    assert plan.pruning_decision.reason == "value_below_threshold"
    assert plan.expansion_policy == ExpansionPolicy(0, 0)
    assert plan.rollout_allocation.rollout_count == 0


def test_valid_branch_returns_complete_plan_and_passes_component_results():
    expected_policy = ExpansionPolicy(5, 20)
    expected_allocation = RolloutAllocation("branch-1", 7, "test allocation")

    class FixedAdaptivePolicy:
        def policy_for(self, importance, branch_value, confidence):
            assert importance == 0.8
            assert branch_value.value == 0.8
            assert confidence == 0.25
            return expected_policy

    class FixedRolloutManager:
        def allocate(self, branch_id, branch_value, confidence, importance):
            assert (branch_id, branch_value, confidence, importance) == (
                "branch-1", 0.8, 0.25, 0.8
            )
            return expected_allocation

    class FixedPriority:
        def calculate(self, branch_value, confidence):
            assert branch_value.value == 0.8
            assert confidence == 0.25
            return 0.95

    controller = make_controller(
        priority_calculator=FixedPriority(),
        adaptive_policy=FixedAdaptivePolicy(),
        rollout_manager=FixedRolloutManager(),
    )
    branch = StoryBranch("branch-1", None, "world", 0, None)

    plan = controller.plan(branch, BranchValue("branch-1", 0.8, ()), 0.25, 0.8)

    assert plan.should_explore
    assert plan.priority == 0.95
    assert plan.expansion_policy is expected_policy
    assert plan.rollout_allocation is expected_allocation
    assert plan.pruning_decision == PruningDecision("branch-1", True, "value_threshold_passed")


def test_optional_constraint_and_role_checks_reach_pruner():
    controller = make_controller()
    branch = StoryBranch("branch-1", None, "world", 0, None)

    plan = controller.plan(
        branch,
        BranchValue("branch-1", 0.8, ()),
        0.5,
        0.5,
        constraint_checks=(ConstraintCheck("canon", True, "valid"),),
        role_state_checks=(RoleStateCheck("hero", True, "valid"),),
    )

    assert plan.should_explore


def test_exploration_plan_is_immutable_and_validates_branch_id():
    controller = make_controller()
    branch = StoryBranch("branch-1", None, "world", 0, None)
    plan = controller.plan(branch, BranchValue("branch-1", 0.8, ()), 0.5, 0.5)

    with pytest.raises(FrozenInstanceError):
        plan.priority = 0.1
    with pytest.raises(ValueError, match="branch_id"):
        ExplorationPlan(
            " ",
            False,
            0,
            ExpansionPolicy(0, 0),
            RolloutAllocation("branch-1", 0, "pruned"),
            PruningDecision("branch-1", False, "pruned"),
        )
