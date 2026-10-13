from cognitive_sandbox.authority import AuthorityManager, CharacterAuthority
from cognitive_sandbox.character_presence import CharacterPresence, PresenceManager, PresenceState
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.encounter import EncounterManager
from cognitive_sandbox.event.event_pipeline import EventPipeline
from cognitive_sandbox.relationship.lifecycle import RelationshipLifecycleManager, RelationshipStage
from cognitive_sandbox.relationship.relationship_manager import RelationshipManager


def test_first_encounter_sets_acquaintance_without_trust_increase():
    relations = RelationshipManager()
    lifecycle = RelationshipLifecycleManager(relations, character_ids=("player", "npc"))
    presence = PresenceManager((
        CharacterPresence("player", "market", PresenceState.ACTIVE, PresenceState.ACTIVE),
        CharacterPresence("npc", "market", PresenceState.INTRODUCED, PresenceState.INTRODUCED),
    ))
    manager = EncounterManager(
        authority_manager=AuthorityManager((CharacterAuthority.player("player"),
                                            CharacterAuthority.important_character("npc")),
                                           player_character_id="player"),
        relationship_manager=relations, relationship_lifecycle_manager=lifecycle,
        presence_manager=presence,
    )
    pipeline = EventPipeline(relationship_manager=relations)
    pipeline.subscribe(lifecycle, name="lifecycle")
    pipeline.subscribe(manager, name="encounters")
    pipeline.publish(WorldEvent("npc-action", "main", "w", "npc_investigated", "npc",
                                {"action_type": "investigate", "description": "角色调查线索"},
                                location="market", timestamp="2026-01-01T20:00:00+00:00"))
    output = pipeline.publish(WorldEvent("player-action", "main", "w", "observe_action", "player",
                                         {"description": "玩家观察周围"}, location="market",
                                         timestamp="2026-01-01T20:15:00+00:00"))
    encounter = next(item for item in output if item.event_type == "social_encounter")
    assert lifecycle.stage_for("player", "npc") is RelationshipStage.ACQUAINTANCE
    assert relations.get_relationship("player", "npc").trust == 0
    assert {encounter.actor_id, encounter.target_id} == {"player", "npc"}
