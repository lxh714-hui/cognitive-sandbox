from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.knowledge.context.knowledge_context_builder import KnowledgeContextBuilder
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.propagation.propagation_engine import PropagationEngine
from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore


def _fact(fact_id="fact-lab", *, importance=0.5, content="玩家进入地下实验室"):
    return WorldFact(fact_id, content, "entry", "2026-10-12T10:00:00+00:00", ("player", "lab"), importance)


def test_world_fact_and_character_knowledge_are_separate():
    fact = _fact()
    store = KnowledgeStore()
    store.add_fact(fact)

    assert store.query("player") == ()
    assert store.get_fact(fact.id) == fact


def test_participants_receive_direct_knowledge_but_nonparticipants_do_not():
    fact = _fact()
    records = PropagationEngine().propagate(
        fact, participants=("player",),
    )
    store = KnowledgeStore()
    store.add_fact(fact)
    for record in records:
        store.add_knowledge(record)

    assert len(store.query("player")) == 1
    assert store.query("resident") == ()
    assert records[0].knowledge_type is KnowledgeType.DIRECT
    assert records[0].known_content == "你亲身经历了：玩家进入地下实验室"


def test_propagation_sources_have_distinct_confidence_and_non_direct_summary():
    records = PropagationEngine().propagate(
        _fact(),
        participants=("player",),
        observers=("guard",),
        rumor_recipients=("resident",),
        summaries={"guard": "监控记录显示有人进入。"},
    )
    by_owner = {record.owner_id: record for record in records}

    assert by_owner["player"].confidence == 1.0
    assert by_owner["guard"].confidence == 0.8
    assert by_owner["resident"].confidence == 0.35
    assert by_owner["guard"].known_content == "监控记录显示有人进入。"
    assert "地下实验室" not in by_owner["guard"].known_content
    assert "地下实验室" not in by_owner["resident"].known_content


def test_retrieval_never_leaks_hidden_or_other_characters_knowledge():
    store = KnowledgeStore()
    secret = _fact(content="地下实验室存有隐藏档案")
    store.add_fact(secret)
    record = KnowledgeRecord(
        owner_id="guard", fact_id=secret.id, knowledge_type="DIRECT",
        source=KnowledgeSource("source-1", "direct", "亲身经历", "guard"),
        confidence=1.0, created_at="2026-10-12T10:00:00+00:00",
        known_content="我在实验室看到了相关情况。",
    )
    store.add_knowledge(record)
    retriever = KnowledgeRetriever(store)

    assert retriever.retrieve("player", "隐藏档案") == ()
    assert retriever.retrieve("guard", "实验室") == (record,)


def test_high_importance_knowledge_ranks_first():
    store = KnowledgeStore()
    old = _fact("low", importance=0.1)
    important = _fact("high", importance=0.95)
    store.add_fact(old)
    store.add_fact(important)
    for fact in (old, important):
        store.add_knowledge(KnowledgeRecord(
            owner_id="player", fact_id=fact.id, knowledge_type="DIRECT",
            source=KnowledgeSource(f"src-{fact.id}", "direct", "亲历"),
            confidence=1.0, created_at=fact.timestamp, known_content="发现实验室入口。",
        ))

    result = KnowledgeRetriever(store).retrieve("player", KnowledgeQuery("实验室", limit=2))

    assert tuple(record.fact_id for record in result) == ("high", "low")


def test_context_builder_uses_scoped_knowledge_and_allowlisted_scene_not_world_state():
    store = KnowledgeStore()
    fact = _fact()
    store.add_fact(fact)
    record, = PropagationEngine().propagate(fact, participants=("player",))
    store.add_knowledge(record)
    builder = KnowledgeContextBuilder(KnowledgeRetriever(store))

    context = builder.build(
        "player", "实验室",
        current_context={
            "location": "地下通道",
            "visible_objects": [{"id": "secret_door_id", "name": "铁门", "hidden_history": "密室"}],
            "danger_level": 0.9,
            "hidden_world_fact": "secret",
        },
        related_memories=("曾经找到入口",),
        available_information=("门上有新鲜划痕",),
    )

    assert context["known_facts"][0]["content"] == record.known_content
    assert context["current_context"] == {
        "location": "地下通道", "visible_objects": ({"name": "铁门"},)
    }
    assert "danger_level" not in context["current_context"]
    assert "hidden_world_fact" not in context["current_context"]
    with pytest.raises(TypeError):
        context["current_context"]["location"] = "changed"


def test_models_are_immutable_and_visibility_can_be_explicitly_shared():
    record = KnowledgeRecord(
        "guard", "fact", KnowledgeType.REPORTED,
        KnowledgeSource("radio", "report", "无线电报告"), 0.7,
        "2026-10-12T10:00:00+00:00", "有人进入了设施。",
        KnowledgeVisibility(("player",)),
    )
    with pytest.raises(FrozenInstanceError):
        record.confidence = 0.1
    store = KnowledgeStore()
    fact = _fact("fact")
    store.add_fact(fact)
    store.add_knowledge(record)

    assert store.query("player")
    assert store.query("resident") == ()
