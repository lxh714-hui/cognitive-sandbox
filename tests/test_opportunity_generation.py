from datetime import datetime, timezone

from cognitive_sandbox.conflict.conflict_state import ConflictState, ConflictStatus
from cognitive_sandbox.conflict.conflict_type import ConflictType
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.lifecycle.goal_state import GoalState
from cognitive_sandbox.narrative.opportunity import EventEmergenceEvaluator, OpportunitySourceType


def test_goal_stagnation_and_escalating_conflict_create_optional_opportunities():
    goal = CharacterGoal("npc-a", "寻找线索", "investigate", .7)
    conflict = ConflictState("c-1", ConflictType.INFORMATION_CONFLICT, ("npc-a", "npc-b"),
                             severity=.8, status=ConflictStatus.ESCALATING)
    before = (goal, conflict)
    opportunities = EventEmergenceEvaluator().evaluate(
        world_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
        active_goals=(goal,), goal_states=(GoalState(goal.goal_id, goal.owner_id, stagnation_level=.8),),
        active_conflicts=(conflict,),
    )
    assert {item.source_type for item in opportunities} == {
        OpportunitySourceType.GOAL, OpportunitySourceType.CONFLICT,
    }
    assert before == (goal, conflict)
    assert all(item.possible_actions for item in opportunities)
