from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.game_launcher import GameLauncher


def test_natural_phrases_resolve_to_rest_and_explore_intents():
    parser = ActionIntentParser()

    rest = parser.parse("player", "我有点累了，回房间休息。")
    explore = parser.parse("player", "我想去街上看看有没有什么异常。")

    assert rest.intent == "rest"
    assert rest.parameters["emotion"] == "tired"
    assert explore.intent == "explore"
    assert explore.object == "街上"


def test_implicit_conversation_preference_is_structured_without_creating_facts():
    intent = ActionIntentParser().parse("player", "我不想再提那件事。")

    assert intent.intent == "talk"
    assert intent.parameters["conversation_preference"] == "avoid_topic"
    assert "world_state" not in intent.parameters


def test_conversation_preference_is_recorded_on_session_without_world_mutation():
    session = GameLauncher(action_interpreter=AIActionInterpreter()).start_scenario("post_apocalypse_city")
    original_world_state = dict(session.world_state)
    session.submit_input("我不想再提那件事。")
    session.confirm()

    assert session.conversation_preferences == [{
        "actor_id": session.player_id,
        "preference": "avoid_topic",
        "topic": None,
    }]
    assert dict(session.world_state) == original_world_state


def test_natural_action_fallback_is_used_when_ai_is_unavailable():
    action = AIActionInterpreter().interpret_action("player", "我想去街上看看有没有什么异常。")

    assert action is not None
    assert action.intent == "explore"
    assert action.raw_input == "我想去街上看看有没有什么异常。"
