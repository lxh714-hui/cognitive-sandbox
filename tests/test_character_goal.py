from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_evaluator import GoalEvaluator
from cognitive_sandbox.goal.goal_manager import GoalManager


def test_goal_is_immutable_and_manager_returns_owner_scoped_goals():
    goal = CharacterGoal("doctor", "修复医疗站", "repair_clinic", .7, ("materials_needed",))
    manager = GoalManager((goal, CharacterGoal("guard", "巡逻", "protect_city", .8)))
    assert manager.for_character("doctor") == (goal,)
    with pytest.raises(FrozenInstanceError):
        goal.progress = .5


def test_goal_evaluator_uses_rules_without_creating_goals():
    goal = CharacterGoal("doctor", "修复医疗站", "repair_clinic", conditions=("materials_needed",))
    evaluator = GoalEvaluator()
    assert evaluator.is_actionable(goal, world_state={"clinic_repaired": False})
    assert not evaluator.is_actionable(goal, world_state={"clinic_repaired": True})
    assert goal.progress == 0


def test_goal_fields_are_validated():
    with pytest.raises(ValueError):
        CharacterGoal("doctor", "repair", "repair", priority=1.2)
