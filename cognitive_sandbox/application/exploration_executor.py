from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from cognitive_sandbox.application.lazy_expander import LazyExpander
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    ExplorationExecutionResult,
    ExplorationPlan,
    StoryBranch,
)


class RolloutSimulationPort(Protocol):
    """Batch interface for executing the rollouts allocated to one branch."""

    def execute_rollouts(
        self,
        branch: StoryBranch,
        rollout_count: int,
    ) -> Sequence[object]: ...


class ExplorationExecutor:
    """Execute one approved exploration plan without managing a search loop."""

    def __init__(
        self,
        lazy_expander: LazyExpander,
        simulation_executor: RolloutSimulationPort,
    ) -> None:
        if not callable(getattr(lazy_expander, "expand", None)):
            raise TypeError("lazy_expander must provide expand().")
        if not callable(getattr(simulation_executor, "execute_rollouts", None)):
            raise TypeError("simulation_executor must provide execute_rollouts().")
        self._lazy_expander = lazy_expander
        self._simulation_executor = simulation_executor

    def execute(
        self,
        plan: ExplorationPlan,
        branch: StoryBranch,
        candidates: Iterable[ActionCandidate],
    ) -> ExplorationExecutionResult:
        if not isinstance(plan, ExplorationPlan):
            raise TypeError("plan must be an ExplorationPlan.")
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        if plan.branch_id != branch.branch_id:
            raise ValueError("plan and branch IDs must match.")
        if plan.pruning_decision.branch_id != branch.branch_id:
            raise ValueError("plan pruning decision must belong to the branch.")
        if not plan.should_explore:
            return ExplorationExecutionResult(branch.branch_id, False, 0, 0, 0)

        expanded = self._lazy_expander.expand(branch, candidates, plan.expansion_policy)
        if isinstance(expanded, (str, bytes)):
            raise TypeError("lazy_expander.expand must return StoryBranch values.")
        expanded_branches = tuple(expanded)
        if any(not isinstance(item, StoryBranch) for item in expanded_branches):
            raise TypeError("lazy_expander.expand must return StoryBranch values.")

        rollout_count = plan.rollout_allocation.rollout_count
        feedbacks: Sequence[object] = ()
        if rollout_count:
            feedbacks = self._simulation_executor.execute_rollouts(branch, rollout_count)
            if isinstance(feedbacks, (str, bytes)):
                raise TypeError("execute_rollouts must return a collection of feedback values.")
            if not isinstance(feedbacks, Sequence):
                feedbacks = tuple(feedbacks)

        return ExplorationExecutionResult(
            branch_id=branch.branch_id,
            executed=True,
            expanded_count=len(expanded_branches),
            rollout_count=rollout_count,
            feedback_count=len(feedbacks),
        )
