from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.application.adaptive_exploration_policy import AdaptiveExplorationPolicy
from cognitive_sandbox.application.branch_pruner import BranchPruner
from cognitive_sandbox.application.rollout_manager import RolloutManager
from cognitive_sandbox.application.search_priority import SearchPriorityCalculator
from cognitive_sandbox.domain.story import (
    BranchValue,
    ConstraintCheck,
    ExplorationPlan,
    ExpansionPolicy,
    PruningDecision,
    PruningPolicy,
    RoleStateCheck,
    RolloutAllocation,
    StoryBranch,
)


class ExplorationController:
    """Coordinate pruning, priority, expansion budget, and rollout allocation."""

    def __init__(
        self,
        *,
        branch_pruner: BranchPruner,
        priority_calculator: SearchPriorityCalculator,
        adaptive_exploration_policy: AdaptiveExplorationPolicy,
        rollout_manager: RolloutManager,
        pruning_policy: PruningPolicy | None = None,
    ) -> None:
        if not callable(getattr(branch_pruner, "decide", None)):
            raise TypeError("branch_pruner must provide a decide method.")
        if not callable(getattr(priority_calculator, "calculate", None)):
            raise TypeError("priority_calculator must provide a calculate method.")
        if not callable(getattr(adaptive_exploration_policy, "policy_for", None)):
            raise TypeError("adaptive_exploration_policy must provide a policy_for method.")
        if not callable(getattr(rollout_manager, "allocate", None)):
            raise TypeError("rollout_manager must provide an allocate method.")
        selected_pruning_policy = pruning_policy or PruningPolicy()
        if not isinstance(selected_pruning_policy, PruningPolicy):
            raise TypeError("pruning_policy must be a PruningPolicy.")
        self._branch_pruner = branch_pruner
        self._priority_calculator = priority_calculator
        self._adaptive_exploration_policy = adaptive_exploration_policy
        self._rollout_manager = rollout_manager
        self._pruning_policy = selected_pruning_policy

    def plan(
        self,
        branch: StoryBranch,
        branch_value: BranchValue,
        confidence: float,
        importance: float,
        *,
        constraint_checks: Iterable[ConstraintCheck] | None = None,
        role_state_checks: Iterable[RoleStateCheck] | None = None,
    ) -> ExplorationPlan:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        if not isinstance(branch_value, BranchValue):
            raise TypeError("branch_value must be a BranchValue.")
        if branch_value.branch_id != branch.branch_id:
            raise ValueError("branch_value must belong to the planned branch.")

        decision = self._branch_pruner.decide(
            branch,
            branch_value,
            self._pruning_policy,
            constraint_checks,
            role_state_checks,
        )
        if not isinstance(decision, PruningDecision):
            raise TypeError("branch_pruner.decide must return a PruningDecision.")
        if decision.branch_id != branch.branch_id:
            raise ValueError("pruning decision must belong to the planned branch.")
        if not decision.kept:
            return ExplorationPlan(
                branch_id=branch.branch_id,
                should_explore=False,
                priority=0.0,
                expansion_policy=ExpansionPolicy(0, 0),
                rollout_allocation=RolloutAllocation(
                    branch.branch_id, 0, "branch rejected by pruning decision"
                ),
                pruning_decision=decision,
            )

        priority = self._priority_calculator.calculate(branch_value, confidence)
        expansion_policy = self._adaptive_exploration_policy.policy_for(
            importance, branch_value, confidence
        )
        rollout_allocation = self._rollout_manager.allocate(
            branch.branch_id, branch_value.value, confidence, importance
        )
        if not isinstance(expansion_policy, ExpansionPolicy):
            raise TypeError("adaptive_exploration_policy.policy_for must return ExpansionPolicy.")
        if not isinstance(rollout_allocation, RolloutAllocation):
            raise TypeError("rollout_manager.allocate must return RolloutAllocation.")
        return ExplorationPlan(
            branch_id=branch.branch_id,
            should_explore=True,
            priority=priority,
            expansion_policy=expansion_policy,
            rollout_allocation=rollout_allocation,
            pruning_decision=decision,
        )
