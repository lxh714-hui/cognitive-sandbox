from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.application.exploration_controller import ExplorationController
from cognitive_sandbox.application.exploration_executor import ExplorationExecutor
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    BranchValue,
    ConstraintCheck,
    ExplorationExecutionResult,
    ExplorationLoopPolicy,
    ExplorationLoopResult,
    RoleStateCheck,
    StoryBranch,
)


class ExplorationLoopManager:
    """Schedule a finite sequence of plan and execution steps."""

    def __init__(
        self,
        controller: ExplorationController,
        executor: ExplorationExecutor,
    ) -> None:
        if not callable(getattr(controller, "plan", None)):
            raise TypeError("controller must provide plan().")
        if not callable(getattr(executor, "execute", None)):
            raise TypeError("executor must provide execute().")
        self._controller = controller
        self._executor = executor

    def run(
        self,
        branch: StoryBranch,
        branch_value: BranchValue,
        confidence: float,
        importance: float,
        candidates: Iterable[ActionCandidate],
        policy: ExplorationLoopPolicy,
        *,
        constraint_checks: Iterable[ConstraintCheck] | None = None,
        role_state_checks: Iterable[RoleStateCheck] | None = None,
    ) -> ExplorationLoopResult:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        if not isinstance(branch_value, BranchValue):
            raise TypeError("branch_value must be a BranchValue.")
        if branch_value.branch_id != branch.branch_id:
            raise ValueError("branch_value must belong to the loop branch.")
        if not isinstance(policy, ExplorationLoopPolicy):
            raise TypeError("policy must be an ExplorationLoopPolicy.")
        candidate_values = tuple(candidates)
        if any(not isinstance(candidate, ActionCandidate) for candidate in candidate_values):
            raise TypeError("candidates must contain ActionCandidate values.")
        constraints = None if constraint_checks is None else tuple(constraint_checks)
        role_checks = None if role_state_checks is None else tuple(role_state_checks)

        iterations = executed_count = total_feedback_count = 0
        stopped_reason = "max_iterations_reached"

        for _ in range(policy.max_iterations):
            plan = self._controller.plan(
                branch,
                branch_value,
                confidence,
                importance,
                constraint_checks=constraints,
                role_state_checks=role_checks,
            )
            result = self._executor.execute(plan, branch, candidate_values)
            if not isinstance(result, ExplorationExecutionResult):
                raise TypeError("executor.execute must return an ExplorationExecutionResult.")
            if result.branch_id != branch.branch_id:
                raise ValueError("executor returned a result for a different branch.")

            iterations += 1
            executed_count += int(result.executed)
            total_feedback_count += result.feedback_count
            if policy.stop_on_no_feedback and result.feedback_count == 0:
                stopped_reason = "no_feedback"
                break

        return ExplorationLoopResult(
            iterations=iterations,
            executed_count=executed_count,
            total_feedback_count=total_feedback_count,
            stopped_reason=stopped_reason,
        )
