import pytest

from cognitive_sandbox.goal.lifecycle import GoalTransitionRule


def test_transition_rule_is_immutable_and_validates_fields():
    rule = GoalTransitionRule("investigate", "progress>=0.5", "confirm", "Confirm clue", .7, ["evidence"])
    assert rule.result_conditions == ("evidence",)
    with pytest.raises((AttributeError, TypeError)):
        rule.result = "other"
    with pytest.raises(ValueError):
        GoalTransitionRule("", "progress>=.5", "next")
    with pytest.raises(ValueError):
        GoalTransitionRule("investigate", "progress>=.5", "next", result_priority=1.1)
