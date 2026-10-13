from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.ai_context_builder import AIContextBuilder
from cognitive_sandbox.application.ai_gm_adapter import AIGMAdapter
from cognitive_sandbox.application.character_dialogue_service import CharacterDialogueService
from cognitive_sandbox.application.character_mind_builder import CharacterMindBuilder
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.character_mind import KnowledgeContext
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.ai_gm import AIGMResponse
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.propagation.propagation_engine import PropagationEngine
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore


class KnowledgeEchoProvider:
    """Test provider can only form its line from the supplied AI context."""

    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        speaker = request.context["speaker"]
        facts = speaker["knowledge_context"]["known_facts"]
        if facts:
            return AIGMResponse(f"我知道：{facts[0]['content']}")
        return AIGMResponse("我还不知道具体发生了什么。")


def _agent(character_id, name, traits=()):
    state = CharacterState(character_id, name, "居民", tuple(traits), (), (), ())
    return AgentContext(character_id, state, (), (), {"secret_world_value": "do not expose"})


def _card(character_id, name):
    return CharacterCard(character_id, name, occupation="居民", personality=("谨慎",))


def _store_with_records():
    store = KnowledgeStore()
    basement = WorldFact(
        "fact-basement", "玩家秘密进入地下室", "entry", "t1", ("player", "doctor"), 0.9
    )
    store.add_fact(basement)
    propagation = PropagationEngine(clock=lambda: "t2")
    records = propagation.propagate(
        basement,
        participants=("player",),
        observers=("doctor",),
        summaries={"doctor": "有人进入地下室"},
    )
    for record in records:
        store.add_knowledge(record)

    help_fact = WorldFact("fact-help", "玩家帮助了医生", "help", "t3", ("player", "doctor"), 0.7)
    store.add_fact(help_fact)
    for record in propagation.propagate(help_fact, participants=("doctor",)):
        store.add_knowledge(record)
    return store


def test_secret_event_is_character_scoped_in_ai_dialogue():
    store = _store_with_records()
    provider = KnowledgeEchoProvider()
    service = CharacterDialogueService(AIGMAdapter(provider, knowledge_retriever=KnowledgeRetriever(store)))

    player_line = service.generate_with_context(
        _agent("player", "玩家"), None, "地下室发生了什么？",
        character_mind=CharacterMindBuilder().build(_card("player", "玩家")),
    )
    doctor_line = service.generate_with_context(
        _agent("doctor", "林夏"), None, "地下室发生了什么？",
        character_mind=CharacterMindBuilder().build(_card("doctor", "林夏")),
        current_event="有人进入地下室",
    )

    assert isinstance(player_line, DialogueLine)
    assert "玩家秘密进入地下室" in player_line.text
    assert isinstance(doctor_line, DialogueLine)
    assert "有人进入地下室" in doctor_line.text
    assert "玩家秘密进入地下室" not in doctor_line.text
    doctor_context = provider.requests[-1].context["speaker"]
    assert all("玩家秘密进入地下室" not in item["content"] for item in doctor_context["knowledge_context"]["known_facts"])


def test_character_can_reference_help_event_they_know():
    service = CharacterDialogueService(
        AIGMAdapter(KnowledgeEchoProvider(), knowledge_retriever=KnowledgeRetriever(_store_with_records()))
    )

    line = service.generate_with_context(
        _agent("doctor", "林夏"), None, "有人帮助了你。",
        character_mind=CharacterMindBuilder().build(_card("doctor", "林夏")),
        current_event="玩家帮助了医生",
    )

    assert line is not None
    assert "玩家帮助了医生" in line.text


def test_same_question_uses_different_character_knowledge():
    store = KnowledgeStore()
    fact = WorldFact("fact-door", "门口传来三声敲门", "sound", "t1", (), 0.5)
    store.add_fact(fact)
    for character_id, content in (("doctor", "我听见门口有敲门声"), ("soldier", "我看见门口有人影")):
        store.add_knowledge(
            KnowledgeRecord(
                character_id,
                fact.id,
                KnowledgeType.OBSERVED,
                KnowledgeSource(f"src-{character_id}", "observation", "现场观察"),
                0.8,
                "t2",
                content,
                KnowledgeVisibility(),
            )
        )
    provider = KnowledgeEchoProvider()
    service = CharacterDialogueService(AIGMAdapter(provider, knowledge_retriever=KnowledgeRetriever(store)))

    doctor_line = service.generate_with_context(
        _agent("doctor", "林夏"), None, "门外是什么情况？",
        character_mind=CharacterMindBuilder().build(_card("doctor", "林夏")),
    )
    soldier_line = service.generate_with_context(
        _agent("soldier", "周衡"), None, "门外是什么情况？",
        character_mind=CharacterMindBuilder().build(_card("soldier", "周衡")),
    )

    assert doctor_line.text != soldier_line.text
    assert "敲门声" in doctor_line.text
    assert "人影" in soldier_line.text


def test_ai_context_excludes_full_world_state_and_hidden_knowledge():
    store = _store_with_records()
    mind = CharacterMindBuilder().build(_card("doctor", "林夏"))
    context = AIContextBuilder(KnowledgeRetriever(store)).build(
        mind,
        character_id="doctor",
        knowledge_query="地下室",
        current_scene={
            "location": "诊所",
            "world_state": {"secret": "hidden"},
            "hidden_facts": ("玩家秘密进入地下室",),
            "visible_events": ("有人进入地下室",),
        },
    )

    assert context["current_scene"] == {"location": "诊所", "visible_events": ("有人进入地下室",)}
    assert "world_state" not in context["current_scene"]
    assert "secret_world_value" not in repr(context)
    assert "玩家秘密进入地下室" not in repr(context)
    assert "有人进入地下室" in repr(context)


def test_character_knowledge_context_is_immutable_and_owner_scoped():
    record = _store_with_records().query("doctor")[0][0]
    source = [record]
    knowledge = KnowledgeContext(source, owner_id="doctor")
    source.clear()
    mind = CharacterMindBuilder().build(_card("doctor", "林夏"), knowledge_context=knowledge)

    assert mind.knowledge_context.records == (record,)
    with pytest.raises(FrozenInstanceError):
        mind.knowledge_context = KnowledgeContext()
    with pytest.raises(FrozenInstanceError):
        knowledge.records = ()
    mismatched_mind = CharacterMindBuilder().build(
        _card("doctor", "林夏"), knowledge_context=KnowledgeContext((record,), owner_id="player")
    )
    with pytest.raises(ValueError):
        AIContextBuilder().build(mismatched_mind, character_id="doctor", current_scene={})


def test_ai_dialogue_failure_uses_existing_rule_fallback():
    class FailingProvider:
        def complete(self, request):
            return AIGMResponse("LLM provider error: offline")

    service = CharacterDialogueService(AIGMAdapter(FailingProvider()))
    line = service.generate_with_context(
        _agent("doctor", "林夏", ("compassionate",)),
        None,
        "help",
        character_mind=CharacterMindBuilder().build(_card("doctor", "林夏")),
    )

    assert line == DialogueLine("doctor", "我只是做了应该做的事。", "calm")
