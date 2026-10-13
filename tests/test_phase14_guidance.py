from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter


def test_guidance_phrases_resolve_locally_even_when_ai_provider_is_configured():
    class Provider:
        def parse_player_action(self, *_args):
            raise AssertionError("guidance requests should not be sent to the AI")

        def parse_action_intent(self, *_args):
            raise AssertionError("guidance requests should not be sent to the AI")

    interpreter = AIActionInterpreter(ai_adapter=Provider())
    for text in ("然后呢？", "我不知道该干什么"):
        intent = interpreter.interpret_action("player", text)
        assert intent.intent == "seek_guidance"


def test_nearby_observation_and_colloquial_talk_have_structured_intents():
    parser = ActionIntentParser()
    observation = parser.parse("player", "我看看附近有什么")
    talk = parser.parse("player", "和柳依依聊聊")
    assert observation.intent == "observe"
    assert talk.intent == "talk"
    assert talk.target == "柳依依"
