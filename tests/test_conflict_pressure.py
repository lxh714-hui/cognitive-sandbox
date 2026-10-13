from cognitive_sandbox.conflict import ConflictManager, ConflictState, ConflictType
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager
from cognitive_sandbox.narrative.narrative_pressure import NarrativePressureCalculator


def test_conflict_severity_increases_planning_pressure_without_creating_events():
    manager = ConflictManager()
    manager.refresh(goal_pressures=(), current_time="Day 2 09:00")
    manager._states["c"] = ConflictState("c", ConflictType.VALUE_CONFLICT, ("a", "b"), severity=.9)
    pressure = NarrativePressureCalculator().with_conflict_pressure(None, manager.pressure())
    assert pressure.conflict_pressure == .3
    assert pressure.urgency > 0
    assert pressure.unresolved_degree > 0


def test_stagnant_goal_becomes_goal_pressure_for_conflict_detection():
    goal = CharacterGoal("liuyiyi", "调查异常", "investigate", goal_id="investigate")
    lifecycle = GoalLifecycleManager(GoalManager((goal,)))
    for day in range(10):
        lifecycle.record_action_feedback("investigate", action_type="investigate",
            timestamp=f"2026-01-{day + 1:02d}T09:00:00+00:00", result="no_new_information",
            effectiveness=.1, event_id=f"e{day}")
    manager = ConflictManager()
    manager.refresh(goals=(goal,), goal_pressures=manager.goal_pressures(lifecycle))
    state = next(item for item in manager.active_conflicts if item.id == "goal-pressure:investigate")
    assert state.severity >= .3
    assert state.related_goals == ("investigate",)
