from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager, GoalLifecycleState, GoalTransitionRule


def test_goal_lifecycle_tracks_progress_and_transforms_into_followup():
    goal = CharacterGoal("liuyiyi", "寻找异常线索", "investigate_anomaly", goal_id="g1")
    manager = GoalManager((goal,))
    lifecycle = GoalLifecycleManager(manager, (GoalTransitionRule(
        "investigate_anomaly", "progress>=0.5", "confirm_anomaly", "确认异常真实性", .8,
    ),))
    manager.update("liuyiyi", "investigate_anomaly", progress=.25)
    lifecycle.evaluate(source_event_id="evt1", timestamp="day-2")
    assert lifecycle.state_for("g1").state is GoalLifecycleState.PROGRESSING
    assert manager.by_id("g1").status == "active"
    manager.update("liuyiyi", "investigate_anomaly", progress=.5)
    created = lifecycle.evaluate(source_event_id="evt2", timestamp="day-3")
    assert len(created) == 1
    assert created[0].goal_type == "confirm_anomaly"
    assert manager.by_id("g1").status == "completed"
    assert lifecycle.state_for("g1").state is GoalLifecycleState.TRANSFORMED
    assert lifecycle.state_for(created[0].goal_id).state is GoalLifecycleState.ACTIVE
    assert lifecycle.transitions[0].source_event_id == "evt2"
    assert lifecycle.history


def test_lifecycle_supports_explicit_blocked_failed_and_satisfied_states():
    manager = GoalManager((CharacterGoal("npc", "目标", "goal", goal_id="g"),))
    lifecycle = GoalLifecycleManager(manager)
    for state in (GoalLifecycleState.BLOCKED, GoalLifecycleState.FAILED, GoalLifecycleState.SATISFIED):
        lifecycle.set_status("g", state, reason="explicit rule")
        assert lifecycle.state_for("g").state is state
