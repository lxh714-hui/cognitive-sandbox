from __future__ import annotations

import math
from collections.abc import Iterable

from cognitive_sandbox.domain.story import (
    BranchValue,
    ConstraintCheck,
    PruningDecision,
    PruningPolicy,
    RoleStateCheck,
    StoryBranch,
)


class BranchPruner:
    """Filter branches using only their evaluated BranchValue values."""

    def __init__(self, minimum_value: float = 0.0) -> None:
        if isinstance(minimum_value, bool) or not isinstance(minimum_value, (int, float)):
            raise TypeError("minimum_value must be a number between 0 and 1.")
        if not math.isfinite(minimum_value) or not 0 <= minimum_value <= 1:
            raise ValueError("minimum_value must be between 0 and 1.")
        self._minimum_value = float(minimum_value)

    def prune(
        self,
        branches: Iterable[StoryBranch] | StoryBranch,
        branch_values: Iterable[BranchValue] | BranchValue,
        policy: PruningPolicy | None = None,
        constraint_checks: Iterable[ConstraintCheck] | None = None,
        role_state_checks: Iterable[RoleStateCheck] | None = None,
    ) -> tuple[StoryBranch, ...] | PruningDecision:
        if isinstance(branches, StoryBranch):
            if not isinstance(branch_values, BranchValue):
                raise TypeError("branch_values must be a BranchValue for a single branch.")
            return self.decide(
                branches,
                branch_values,
                policy or PruningPolicy(self._minimum_value),
                constraint_checks,
                role_state_checks,
            )
        if policy is not None or constraint_checks is not None or role_state_checks is not None:
            raise TypeError("pruning checks and policy apply only to a single branch.")
        if isinstance(branches, (str, bytes)):
            raise TypeError("branches must contain StoryBranch values.")
        if isinstance(branch_values, (str, bytes)):
            raise TypeError("branch_values must contain BranchValue values.")
        branch_items = tuple(branches)
        value_items = tuple(branch_values)
        if any(not isinstance(branch, StoryBranch) for branch in branch_items):
            raise TypeError("branches must contain only StoryBranch values.")
        if any(not isinstance(value, BranchValue) for value in value_items):
            raise TypeError("branch_values must contain only BranchValue values.")

        branch_ids = tuple(branch.branch_id for branch in branch_items)
        if len(set(branch_ids)) != len(branch_ids):
            raise ValueError("branches must have unique IDs.")
        value_by_id = {value.branch_id: value for value in value_items}
        if len(value_by_id) != len(value_items):
            raise ValueError("branch_values must have unique branch IDs.")
        if set(value_by_id) != set(branch_ids):
            raise ValueError("branch_values must align exactly with branches.")

        return tuple(
            branch
            for branch in branch_items
            if value_by_id[branch.branch_id].value >= self._minimum_value
        )

    def decide(
        self,
        branch: StoryBranch,
        branch_value: BranchValue,
        policy: PruningPolicy,
        constraint_checks: Iterable[ConstraintCheck] | None = None,
        role_state_checks: Iterable[RoleStateCheck] | None = None,
    ) -> PruningDecision:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        if not isinstance(branch_value, BranchValue):
            raise TypeError("branch_value must be a BranchValue.")
        if branch_value.branch_id != branch.branch_id:
            raise ValueError("branch_value must belong to the evaluated branch.")
        if not isinstance(policy, PruningPolicy):
            raise TypeError("policy must be a PruningPolicy.")
        checks = tuple(constraint_checks or ())
        if any(not isinstance(check, ConstraintCheck) for check in checks):
            raise TypeError("constraint_checks must contain ConstraintCheck values.")
        role_checks = tuple(role_state_checks or ())
        if any(not isinstance(check, RoleStateCheck) for check in role_checks):
            raise TypeError("role_state_checks must contain RoleStateCheck values.")

        if any(not check.passed for check in checks):
            return PruningDecision(branch.branch_id, False, "hard_constraint_failed")
        if any(not check.valid for check in role_checks):
            return PruningDecision(branch.branch_id, False, "role_state_invalid")
        if branch_value.value < policy.minimum_value:
            return PruningDecision(branch.branch_id, False, "value_below_threshold")
        return PruningDecision(branch.branch_id, True, "value_threshold_passed")
