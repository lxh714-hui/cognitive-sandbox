import pytest

from cognitive_sandbox.application.branch_pruner import BranchPruner
from cognitive_sandbox.domain.story import (
    BranchValue,
    ConstraintCheck,
    PruningDecision,
    PruningPolicy,
    RoleStateCheck,
    StoryBranch,
)


def _branch(branch_id):
    return StoryBranch(branch_id, "root", "world", 0, None)


def _value(branch_id, value):
    return BranchValue(branch_id, value, ("heuristic",))


def test_pruner_filters_below_threshold_and_preserves_input_order():
    branches = (_branch("a"), _branch("b"), _branch("c"))
    values = (_value("a", 0.2), _value("b", 0.7), _value("c", 0.9))

    kept = BranchPruner(minimum_value=0.7).prune(branches, values)

    assert tuple(branch.branch_id for branch in kept) == ("b", "c")


def test_default_threshold_keeps_all_branches_and_empty_input_is_supported():
    branches = (_branch("a"), _branch("b"))
    values = (_value("a", 0.0), _value("b", 0.4))

    assert BranchPruner().prune(branches, values) == branches
    assert BranchPruner(1.0).prune((), ()) == ()


def test_pruner_validates_threshold_and_branch_value_alignment():
    with pytest.raises(ValueError, match="minimum_value"):
        BranchPruner(-0.1)
    with pytest.raises(TypeError, match="minimum_value"):
        BranchPruner(True)

    with pytest.raises(ValueError, match="align exactly"):
        BranchPruner().prune((_branch("a"),), (_value("b", 0.8),))
    with pytest.raises(ValueError, match="unique"):
        BranchPruner().prune((_branch("a"),), (_value("a", 0.5), _value("a", 0.8)))


def test_pruner_requires_domain_objects():
    with pytest.raises(TypeError, match="only StoryBranch"):
        BranchPruner().prune((object(),), ())
    with pytest.raises(TypeError, match="only BranchValue"):
        BranchPruner().prune((_branch("a"),), (object(),))


def test_hard_constraint_failure_prunes_before_value_threshold():
    decision = BranchPruner(minimum_value=0.9).prune(
        _branch("a"),
        _value("a", 1.0),
        PruningPolicy(minimum_value=0.1),
        (ConstraintCheck("no-death", False, "Forbidden event occurred."),),
    )

    assert decision == PruningDecision("a", False, "hard_constraint_failed")


def test_passed_constraint_does_not_bypass_value_threshold():
    pruner = BranchPruner()
    decision = pruner.prune(
        _branch("a"),
        _value("a", 0.4),
        PruningPolicy(minimum_value=0.6),
        (ConstraintCheck("safe-route", True, "No hard rule was violated."),),
    )

    assert decision.kept is False
    assert decision.reason == "value_below_threshold"


def test_no_constraints_preserve_phase_1341_threshold_behavior():
    branch = _branch("a")
    pruner = BranchPruner(minimum_value=0.6)

    assert pruner.prune(branch, _value("a", 0.6)).kept is True
    assert pruner.prune(branch, _value("a", 0.5)).reason == "value_below_threshold"
    assert pruner.prune((branch,), (_value("a", 0.5),)) == ()


def test_multiple_constraint_checks_prune_if_any_check_fails():
    decision = BranchPruner().decide(
        _branch("a"),
        _value("a", 1.0),
        PruningPolicy(),
        (
            ConstraintCheck("allowed-place", True, "Location is permitted."),
            ConstraintCheck("safe-action", False, "Action is forbidden."),
            ConstraintCheck("valid-time", True, "Time is valid."),
        ),
    )

    assert decision.kept is False
    assert decision.reason == "hard_constraint_failed"


def test_constraint_check_is_immutable_and_validates_fields():
    check = ConstraintCheck("rule-1", True, "Rule passed.")
    with pytest.raises(AttributeError):
        check.passed = False
    with pytest.raises(ValueError, match="constraint_id"):
        ConstraintCheck(" ", False, "failed")
    with pytest.raises(ValueError, match="reason"):
        ConstraintCheck("rule-1", True, " ")


def test_invalid_role_state_prunes_branch():
    decision = BranchPruner().prune(
        _branch("a"),
        _value("a", 0.9),
        PruningPolicy(minimum_value=0.2),
        role_state_checks=(RoleStateCheck("lin-xia", False, "Role state is invalid."),),
    )

    assert decision.kept is False
    assert decision.reason == "role_state_invalid"


def test_valid_role_state_continues_to_value_threshold():
    decision = BranchPruner().prune(
        _branch("a"),
        _value("a", 0.4),
        PruningPolicy(minimum_value=0.6),
        role_state_checks=(RoleStateCheck("lin-xia", True, "Role state is valid."),),
    )

    assert decision.kept is False
    assert decision.reason == "value_below_threshold"


def test_hard_constraint_failure_takes_priority_over_role_state_failure():
    decision = BranchPruner().prune(
        _branch("a"),
        _value("a", 1.0),
        PruningPolicy(minimum_value=0.0),
        constraint_checks=(ConstraintCheck("hard-rule", False, "Hard rule failed."),),
        role_state_checks=(RoleStateCheck("agent-a", False, "Role state failed."),),
    )

    assert decision.reason == "hard_constraint_failed"


def test_role_state_failure_takes_priority_over_value_threshold():
    decision = BranchPruner().decide(
        _branch("a"),
        _value("a", 0.1),
        PruningPolicy(minimum_value=0.9),
        role_state_checks=(RoleStateCheck("agent-a", False, "Role state failed."),),
    )

    assert decision.reason == "role_state_invalid"


def test_multiple_role_checks_prune_if_any_role_is_invalid():
    decision = BranchPruner().decide(
        _branch("a"),
        _value("a", 1.0),
        PruningPolicy(),
        role_state_checks=(
            RoleStateCheck("agent-a", True, "State valid."),
            RoleStateCheck("agent-b", False, "State invalid."),
            RoleStateCheck("agent-c", True, "State valid."),
        ),
    )

    assert decision.kept is False
    assert decision.reason == "role_state_invalid"


def test_role_state_check_is_immutable_and_validates_fields():
    check = RoleStateCheck("agent-a", True, "Valid state.")
    with pytest.raises(AttributeError):
        check.valid = False
    with pytest.raises(ValueError, match="role_id"):
        RoleStateCheck(" ", False, "Invalid state.")
    with pytest.raises(ValueError, match="reason"):
        RoleStateCheck("agent-a", True, " ")
