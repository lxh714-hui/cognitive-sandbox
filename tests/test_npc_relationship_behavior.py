from cognitive_sandbox.application.npc.npc_decision_engine import NpcDecisionEngine
from cognitive_sandbox.domain.character_mind import CharacterMind, Identity, KnowledgeContext, PersonalityProfile
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.history.world_event_record import WorldEventRecord
from cognitive_sandbox.relationship.relationship_state import RelationshipState


def test_same_weapon_event_produces_different_actions_for_trusted_and_hostile_relations():
    engine = NpcDecisionEngine()
    event = WorldEvent("e1", "main", "w1", "weapon_drawn", "player", {}, 1)
    mind = CharacterMind(
        Identity("林队长", "soldier"), PersonalityProfile(),
        knowledge_context=KnowledgeContext(owner_id="soldier"),
    )
    trusted = engine.decide(
        mind, mind.knowledge_context, event,
        (RelationshipState("soldier", "player", trust=60),),
    )
    hostile = engine.decide(
        mind, mind.knowledge_context, event,
        (RelationshipState("soldier", "player", trust=-60, hostility=70),),
    )
    neutral = engine.decide(mind, mind.knowledge_context, event)

    assert trusted[0].action_type == "ask"
    assert hostile[0].action_type == "restrain"
    assert neutral[0].action_type == "warn"


def test_event_history_escalates_repeated_weapon_incident():
    engine = NpcDecisionEngine()
    event = WorldEvent("e2", "main", "w1", "weapon_drawn", "player", {}, 2)
    mind = CharacterMind(
        Identity("林队长", "soldier"), PersonalityProfile(),
        knowledge_context=KnowledgeContext(owner_id="soldier"),
    )
    previous = WorldEventRecord("e1", "weapon_drawn", "day-1", ("player",), (), "market")
    response = engine.decide(mind, mind.knowledge_context, event, history=(previous,))
    assert response[0].action_type == "approach"
