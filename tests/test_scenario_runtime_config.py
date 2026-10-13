from types import SimpleNamespace

from cognitive_sandbox.application.actions.generic_action_handler import GenericActionHandler
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse


class _ResponseProvider:
    def complete(self, request: AIGMRequest) -> AIGMResponse:
        return AIGMResponse('{"action_type":"协助","target":"医护人员"}')


def test_scenario_action_and_entity_aliases_drive_interpretation():
    config = {
        "action_aliases": {"协助": "help"},
        "entity_aliases": {"医护人员": "npc_17"},
    }
    interpreter = AIActionInterpreter(AIGMAdapter(_ResponseProvider())).with_scenario_config(config)

    result = interpreter.interpret("player", "请协助医护人员")

    assert result.intent == "help"
    assert result.target == "npc_17"


def test_generic_action_uses_scenario_location_alias_and_duration():
    handler = GenericActionHandler(runtime_config={
        "location_aliases": {"诊疗点": ["clinic"]},
        "action_durations": {"move": 37},
    })
    clinic = SimpleNamespace(location_id="clinic", name="医务室", tags=())
    action = SimpleNamespace(object="诊疗点")
    context = SimpleNamespace(location_manager=SimpleNamespace(locations=(clinic,)))

    assert handler._destination(action, context, "move") is clinic
    assert handler._durations["move"] == 37


def test_gray_harbor_goal_rules_preserve_existing_roles():
    launcher = GameLauncher()
    example_session = launcher.start_scenario("example_world")
    example_goals = example_session.executor.goal_manager.goals
    assert any(goal.owner_id == "doctor" and goal.goal_type == "repair_clinic" for goal in example_goals)
    assert any(goal.owner_id == "doctor" and goal.goal_type == "collect_materials" for goal in example_goals)

    built_in_session = launcher.start_scenario("post_apocalypse_city")
    assert any(goal.owner_id == "soldier" and goal.goal_type == "protect_city"
               for goal in built_in_session.executor.goal_manager.goals)

