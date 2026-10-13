from cognitive_sandbox.agency.goal_action_generator import GoalActionGenerator
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.goal.goal_manager import GoalManager
from cognitive_sandbox.goal.lifecycle import GoalLifecycleManager, GoalTransitionRule


def test_new_goal_after_transition_becomes_actionable_by_existing_agency_generator():
    manager = GoalManager((CharacterGoal("liuyiyi", "寻找异常线索", "investigate_anomaly",
                                         goal_id="first", progress=.2),))
    lifecycle = GoalLifecycleManager(manager, (GoalTransitionRule(
        "investigate_anomaly", "progress>=0.2", "confirm_anomaly", "确认异常真实性", .85,
    ),))
    created = lifecycle.evaluate(source_event_id="clue-event")
    assert created[0].goal_type == "confirm_anomaly"
    candidates = GoalActionGenerator(({
        "goal_type": "confirm_anomaly", "action_type": "investigate",
        "reason": "scenario-defined confirmation action", "score": .7,
    },)).generate(created[0], ("已知异常线索需要确认",), character_id="liuyiyi")
    assert candidates
    assert candidates[0].action.parameters["goal_id"] == created[0].goal_id
