from cognitive_sandbox.application.ai_context_builder import AIContextBuilder
from cognitive_sandbox.application.character_dialogue_service import CharacterDialogueService
from cognitive_sandbox.cognition import CognitiveEngine, CognitiveStyle
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.dialogue import DialogueLine


class CaptureAdapter:
    def generate_dialogue(self, speaker, target, situation, **kwargs):
        self.kwargs = kwargs
        return "这里有两个地方需要核实。"


def _agent(cid, name):
    return AgentContext(cid, CharacterState(cid, name, "调查者", (), (), (), ()), (), (), {})


def test_dialogue_receives_scoped_cognitive_context_and_generates_line():
    adapter = CaptureAdapter()
    engine = CognitiveEngine(styles={"npc": CognitiveStyle(analytical=.9, suspicious=.8)})
    thought = engine.interpret_event("npc", type("E", (), {"event_id": "e", "event_type": "anomaly"})(), ("墙钟时间异常",))
    context = {**dict(engine.context_for("npc")), "current_interpretation": thought}
    line = CharacterDialogueService(adapter).generate_with_context(
        _agent("npc", "林夏"), _agent("player", "玩家"), "询问时间", cognitive_context=context
    )
    assert isinstance(line, DialogueLine)
    assert adapter.kwargs["cognitive_context"]["current_interpretation"] == thought.interpretation
    assert "world_state" not in adapter.kwargs["cognitive_context"]


def test_ai_context_builder_does_not_add_global_state():
    from cognitive_sandbox.application.character_mind_builder import CharacterMindBuilder
    from cognitive_sandbox.domain.character_card import CharacterCard
    mind = CharacterMindBuilder().build(CharacterCard("npc", "林夏"))
    context = AIContextBuilder().build(mind, current_scene={"location": "大厅", "secret_world_fact": "hidden"},
                                       character_id="npc", cognitive_context={"current_interpretation": "可能有异常"})
    assert context["cognitive_context"]["current_interpretation"] == "可能有异常"
    assert "secret_world_fact" not in str(context)
