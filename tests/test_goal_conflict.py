from cognitive_sandbox.conflict import ConflictManager, ConflictType
from cognitive_sandbox.goal.character_goal import CharacterGoal


def test_opposed_character_goals_create_goal_conflict_state():
    manager = ConflictManager()
    goals = (
        CharacterGoal("a", "寻找真相", "investigate", goal_id="truth"),
        CharacterGoal("b", "隐藏真相", "conceal", goal_id="conceal"),
    )
    states = manager.refresh(goals=goals, current_time="Day 1 09:00")
    assert any(item.conflict_type is ConflictType.GOAL_CONFLICT for item in states)
    assert not any(item.event_id if hasattr(item, "event_id") else False for item in states)
