from cognitive_sandbox.authority import AuthorityManager, CharacterAuthority
from cognitive_sandbox.character_presence import CharacterPresence, PresenceManager, PresenceState
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.encounter import EncounterManager
from cognitive_sandbox.event.event_pipeline import EventPipeline, KnowledgeEventListener
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.knowledge.retrieval.knowledge_query import KnowledgeQuery
from cognitive_sandbox.knowledge.retrieval.knowledge_retriever import KnowledgeRetriever
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore


def test_encounter_shares_only_public_contact_and_not_hidden_knowledge():
    store = KnowledgeStore()
    fact = WorldFact("secret", "柳依依掌握的隐藏异常真相", "secret", "t0", ("npc",), .9)
    store.add_fact(fact)
    store.add_knowledge(KnowledgeRecord("npc", "secret", KnowledgeType.DIRECT,
                                        KnowledgeSource("src", "private", "private"), .9, "t0",
                                        "柳依依掌握的隐藏异常真相"))
    retriever = KnowledgeRetriever(store)
    presence = PresenceManager((
        CharacterPresence("player", "market", PresenceState.ACTIVE, PresenceState.ACTIVE),
        CharacterPresence("npc", "market", PresenceState.INTRODUCED, PresenceState.INTRODUCED),
        CharacterPresence("bystander", "market", PresenceState.ACTIVE, PresenceState.ACTIVE),
    ))
    manager = EncounterManager(
        authority_manager=AuthorityManager((CharacterAuthority.player("player"),
                                            CharacterAuthority.important_character("npc"),
                                            CharacterAuthority.important_character("bystander")),
                                           player_character_id="player"),
        presence_manager=presence, knowledge_retriever=retriever,
    )
    pipeline = EventPipeline(knowledge_handler=KnowledgeEventListener(store))
    pipeline.subscribe(manager, name="encounters")
    pipeline.publish(WorldEvent("npc-action", "main", "w", "npc_investigated", "npc",
                                {"description": "角色正在调查附近线索", "action_type": "investigate"},
                                location="market", timestamp="2026-01-01T20:00:00+00:00"))
    output = pipeline.publish(WorldEvent("player-action", "main", "w", "observe_action", "player",
                                         {"description": "玩家观察周围"}, location="market",
                                         timestamp="2026-01-01T20:15:00+00:00"))
    contact = next(item for item in output if item.event_type == "social_encounter")
    player_records = retriever.retrieve("player", KnowledgeQuery(limit=100))
    bystander_records = retriever.retrieve("bystander", KnowledgeQuery(limit=100))
    assert any(contact.payload["description"] in item.known_content for item in player_records)
    assert not any(item.fact_id == f"fact_{contact.event_id}" for item in bystander_records)
    assert not any("隐藏异常真相" in item.known_content for item in player_records)
