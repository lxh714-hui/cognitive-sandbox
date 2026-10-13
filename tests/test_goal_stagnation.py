from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager, GoalState


def test_repeated_ineffective_goal_actions_raise_stagnation_and_frustration():
    goal = CharacterGoal("liuyiyi", "调查异常", "investigate", goal_id="investigate")
    lifecycle = GoalLifecycleManager(GoalManager((goal,)))
    for day in range(10):
        lifecycle.record_action_feedback(
            "investigate", action_type=("investigate", "organize", "observe")[day % 3],
            timestamp=f"2026-01-{day + 1:02d}T09:00:00+00:00",
            result="no_new_information", effectiveness=.1, event_id=f"e{day}",
        )
    state = lifecycle.state_for("investigate")
    assert state.stagnation_level >= .65
    assert state.frustration_level > 0
    assert len(state.recent_action_feedback) == 10


def test_old_goal_state_constructor_and_saved_snapshot_defaults_remain_compatible():
    state = GoalState("g", "npc")
    assert state.progress_velocity == 0
    assert state.stagnation_level == 0
    assert state.frustration_level == 0
    assert state.recent_action_feedback == ()
