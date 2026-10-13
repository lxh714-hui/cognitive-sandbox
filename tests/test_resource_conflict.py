from cognitive_sandbox.conflict import ConflictManager, ConflictType
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.world_evolution.resource_manager import WorldResource


def test_competing_goals_for_scarce_resource_are_detected():
    goals = (CharacterGoal("doctor", "需要药品", "medical", goal_id="medicine"),
             CharacterGoal("merchant", "囤积药品", "stockpile", goal_id="stockpile"))
    resource = WorldResource("medicine", "medicine", 1)
    states = ConflictManager().refresh(goals=goals, resources=(resource,))
    assert any(item.conflict_type is ConflictType.RESOURCE_CONFLICT for item in states)
