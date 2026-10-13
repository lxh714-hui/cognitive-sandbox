from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager
from cognitive_sandbox.world_evolution.world_evolution_engine import WorldEvolutionEngine
from cognitive_sandbox.domain.world_events import WorldEvent


def test_effective_progress_increases_velocity_and_relaxes_stagnation():
    goal = CharacterGoal("npc", "调查线索", "investigate", goal_id="g", progress=.2)
    lifecycle = GoalLifecycleManager(GoalManager((goal,)))
    state = lifecycle.record_action_feedback(
        "g", action_type="investigate", timestamp="2026-04-01T09:00:00+00:00",
        result="progress", effectiveness=.9, progress_delta=.1, event_id="success",
    )
    assert state.progress_velocity > 0
    assert state.stagnation_level == 0
    assert state.frustration_level == 0


def test_failed_action_adds_stagnation_without_changing_goal_progress():
    goal = CharacterGoal("npc", "调查线索", "investigate", goal_id="g", progress=.2)
    manager = GoalManager((goal,))
    lifecycle = GoalLifecycleManager(manager)
    state = lifecycle.record_action_feedback(
        "g", action_type="investigate", timestamp="2026-04-01T09:00:00+00:00",
        result="failed", effectiveness=0, event_id="failed",
    )
    assert manager.by_id("g").progress == .2
    assert state.stagnation_level > 0


def test_no_new_information_investigation_does_not_advance_goal():
    goal = CharacterGoal("npc", "调查线索", "investigate", goal_id="g")
    manager = GoalManager((goal,))
    engine = WorldEvolutionEngine(goal_manager=manager)
    event = WorldEvent(
        "e1", "main", "w", "npc_investigated", "npc",
        {"parameters": {"goal_id": "g", "goal_effect": {
            "result": "no_new_information", "progress_delta": 0,
        }}},
    )
    engine.handle_event(event)
    assert manager.by_id("g").progress == 0
