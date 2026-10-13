from cognitive_sandbox.application.ai_context_builder import AIContextBuilder
from cognitive_sandbox.application.character_mind_builder import CharacterMindBuilder
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.character_mind import RelationshipContext
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.knowledge_visibility import KnowledgeVisibility
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.propagation.propagation_engine import PropagationEngine
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.relationship.relationship_state import RelationshipState


def test_dialogue_context_contains_only_speaker_knowledge_and_scoped_relationship():
    store = KnowledgeStore()
    fact = WorldFact("secret", "梁景曾秘密进入地下室", "entry", "t1", ("liang", "liu"), .9)
    store.add_fact(fact)
    store.add_knowledge(KnowledgeRecord(
        "liu", fact.id, KnowledgeType.REPORTED,
        KnowledgeSource("report", "report", "街区传闻"), .45, "t2",
        "有人进入过地下室", KnowledgeVisibility(),
    ))
    mind = CharacterMindBuilder().build(CharacterCard("liu", "柳依依", goals=("寻找线索",)))
    mind = __import__("dataclasses").replace(mind, relationship_context=RelationshipContext(
        "liu", (RelationshipState("liu", "liang", trust=24),),
    ))
    prompt_context = AIContextBuilder(KnowledgeRetriever(store)).build(
        mind,
        character_id="liu",
        knowledge_query="地下室",
        current_scene={"location": "街区", "world_state": {"secret": "hidden"}},
    )

    facts = tuple(item["content"] for item in prompt_context["knowledge_context"]["known_facts"])
    assert "有人进入过地下室" in facts
    assert all("梁景曾秘密进入地下室" not in item for item in facts)
    assert "world_state" not in prompt_context["current_scene"]
    assert prompt_context["relationship_context"]["relationships"][0]["target"] == "当前交谈对象"
