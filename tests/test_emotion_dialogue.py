from cognitive_sandbox.application.character_dialogue_service import CharacterDialogueService
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.emotion import EmotionalState


def _agent(agent_id, name):
    return AgentContext(agent_id, CharacterState(agent_id, name, "resident", (), (), (), ()), (), (), {})


class _AI:
    def __init__(self):
        self.scene = None

    def generate_dialogue(self, speaker, target, situation, **kwargs):
        self.scene = kwargs["current_scene"]
        return "我需要先确认情况。"


def test_dialogue_ai_receives_emotion_style_and_rule_fallback_reflects_emotion():
    ai = _AI()
    service = CharacterDialogueService(ai)
    speaker = _agent("npc", "梁景")
    line = service.generate_with_context(speaker, None, "有人受伤",
                                        emotional_state=EmotionalState(fear=.8, anger=.6))
    assert line.text == "我需要先确认情况。"
    assert any("不安" in item for item in ai.scene["emotional_style"])

    fallback = CharacterDialogueService().generate_with_context(
        speaker, None, "help", emotional_state=EmotionalState(anger=.8)
    )
    assert fallback is None or fallback.emotion_hint == "angry"
