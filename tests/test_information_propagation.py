from cognitive_sandbox.authority import AuthorityManager, CharacterAuthority
from cognitive_sandbox.character_presence import CharacterPresence, PresenceManager, PresenceState
from cognitive_sandbox.information import InformationManager
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.relationship.relationship_manager import RelationshipManager
from cognitive_sandbox.domain.world_events import WorldEvent


def _manager():
    presence = PresenceManager((
        CharacterPresence("witness", "market", PresenceState.ACTIVE, PresenceState.ACTIVE),
        CharacterPresence("listener", "market", PresenceState.INTRODUCED, PresenceState.INTRODUCED),
        CharacterPresence("far", "home", PresenceState.ACTIVE, PresenceState.ACTIVE),
    ))
    store = KnowledgeStore()
    manager = InformationManager(
        knowledge_store=store,
        authority_manager=AuthorityManager((CharacterAuthority.player("witness"),
                                             CharacterAuthority.important_character("listener"),
                                             CharacterAuthority.important_character("far"))),
        presence_manager=presence, relationship_manager=RelationshipManager(),
    )
    return manager, store


def test_public_clue_spreads_only_to_active_nearby_permitted_characters():
    manager, store = _manager()
    event = WorldEvent("e1", event_type="anomaly_observed", actor_id="witness",
                       payload={"description": "听见街区传来奇怪声音", "importance": .8},
                       location="market", timestamp="day-1")
    manager.handle_event(event)
    assert len(manager.clues) == 1
    assert manager.rumors and manager.rumors[0].current_holder == "listener"
    assert store.query("far") == ()
    assert ("witness", "listener") in tuple(path.holders for path in manager.paths)


def test_hidden_event_does_not_enter_public_propagation_network():
    manager, _ = _manager()
    event = WorldEvent("secret", event_type="secret_event", actor_id="witness",
                       payload={"description": "hidden lab contents", "visibility": "hidden"}, location="market")
    manager.handle_event(event)
    assert manager.clues == ()
    assert manager.rumors == ()


def test_a_holder_can_pass_an_existing_clue_along_a_conversation_path():
    manager, store = _manager()
    # Bring the third character to the same public place for a later meeting.
    from dataclasses import replace
    manager.handle_event(WorldEvent("e1", event_type="anomaly_observed", actor_id="witness",
                                    payload={"description": "街区传来奇怪钟声", "importance": .8},
                                    location="market", timestamp="t1"))
    manager.presence_manager._presences["far"] = replace(
        manager.presence_manager.get("far"), current_location="market"
    )
    manager.handle_event(WorldEvent("talk", event_type="talk_attempt", actor_id="listener", target_id="far",
                                    payload={"description": "两人谈起街区见闻"},
                                    location="market", timestamp="t2"))
    assert any(record.knowledge_type.value == "RUMOR" for record, _ in store.query("far"))
    assert any(path.holders == ("witness", "listener", "far") for path in manager.paths)
