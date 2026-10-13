from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
from cognitive_sandbox.application.roleplay_executor import RoleplayExecutor
from cognitive_sandbox.application.actions.base_handler import ActionExecutionContext
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from copy import deepcopy
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_mind import CharacterMind, Identity, KnowledgeContext, PersonalityProfile, RelationshipContext
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
from cognitive_sandbox.domain.simulation_result import SimulationTickResult
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.persistence.storage.save_repository import JsonSaveRepository
from cognitive_sandbox.persistence.world_save_service import WorldSaveService
from cognitive_sandbox.relationship import RelationshipManager, RelationshipRule, RelationshipState


def test_relationship_initial_state_is_neutral_and_directional():
    manager = RelationshipManager()
    assert manager.get_relationship("player", "doctor") == RelationshipState("player", "doctor")
    manager.set_relationship(RelationshipState("player", "doctor", trust=20))
    assert manager.get_relationship("doctor", "player").trust == 0


def test_world_event_changes_relationship_with_clamped_deltas():
    manager = RelationshipManager()
    event = WorldEvent("e1", "main", "w1", "help_attempt", "player", {"target_id": "doctor"}, 1)
    states = manager.apply_event(event)
    assert manager.get_relationship("player", "doctor").trust == 20
    assert manager.get_relationship("player", "doctor").respect == 10
    assert manager.get_relationship("doctor", "player").trust == 20
    assert len(states) == 2

    bounded = RelationshipManager(
        (RelationshipState("player", "doctor", trust=95),),
        (RelationshipRule(("help_attempt",), trust_delta=20),),
    )
    bounded.apply_event(event)
    assert bounded.get_relationship("player", "doctor").trust == 100

    idempotent = RelationshipManager()
    idempotent.apply_event(event)
    idempotent.apply_event(event)
    assert idempotent.get_relationship("player", "doctor").trust == 20


def test_character_relationship_slice_excludes_other_pairs():
    manager = RelationshipManager((
        RelationshipState("doctor", "player", trust=60),
        RelationshipState("player", "merchant", trust=20),
        RelationshipState("merchant", "doctor", trust=-10),
    ))
    assert manager.for_character("doctor") == (RelationshipState("doctor", "player", trust=60),)


def test_character_mind_relationship_context_is_owner_scoped():
    scoped = RelationshipContext("doctor", (RelationshipState("doctor", "player", trust=60),))
    mind = CharacterMind(Identity("医生", "doctor"), PersonalityProfile(), relationship_context=scoped)
    assert mind.relationship_context.relationships == scoped.relationships
    try:
        RelationshipContext("doctor", (RelationshipState("player", "merchant", trust=20),))
    except ValueError:
        pass
    else:
        raise AssertionError("relationship context accepted another character's relationship")


def test_roleplay_event_automatically_enters_history_and_updates_relationship():
    player = AgentContext("player", CharacterState("player", "玩家", "survivor", (), (), (), ()), (), (), {"location": "clinic"})
    doctor = AgentContext("doctor", CharacterState("doctor", "医生", "doctor", (), (), (), ()), (), (), {"location": "clinic"})
    mind = CharacterMind(Identity("医生", "doctor"), PersonalityProfile(), knowledge_context=KnowledgeContext(owner_id="doctor"))
    event = WorldEvent("saved-doctor", "main", "world", "help_attempt", "player", {}, 1, target_id="doctor", location="clinic", timestamp="day-3")
    executor = RoleplayExecutor(PlayerActionParser(), object(), NarrativeFormatter(), object(), character_minds={"doctor": mind})
    context = ActionExecutionContext(
        RoleplayTurn("turn", "player", "executing", "帮助医生"), player, (player, doctor),
        {"location": "clinic"}, "当前场景", character_minds=executor.character_minds,
        narrative_formatter=NarrativeFormatter(), relationship_manager=executor.relationship_manager,
        event_timeline=executor.event_timeline,
    )
    result = RoleplayResult("turn", True, (), (), SimulationTickResult({}, player, (event,)))

    updated = executor._add_npc_responses(result, context)

    assert [record.event_id for record in executor.event_timeline.events] == ["saved-doctor", updated.simulation_result.events[1].event_id]
    assert executor.relationship_manager.get_relationship("player", "doctor").trust == 20
    assert updated.simulation_result.events[-1].event_type == "npc_respond"


def test_relationships_and_timeline_persist_and_restore(tmp_path):
    launcher = GameLauncher(action_interpreter=PlayerActionParser())
    session = launcher.start_scenario("example_world")
    session.world_instance_id = "instance1"
    session.executor.relationship_manager.set_relationship(RelationshipState("doctor", "player", trust=65, respect=10))
    event = WorldEvent("history-1", "main", "world", "weapon_drawn", "player", {}, 1, target_id="doctor", timestamp="day-2")
    session.executor.event_timeline.record_event(event)
    world = WorldInstance("instance1", "example_world", "world", "Harbor", "A world", "可继续", "day 2", "day-2")
    service = WorldSaveService(JsonSaveRepository(tmp_path / "saves"))
    service.save_world(world, session, created_time="day-1")

    legacy_payload = deepcopy(service.repository.load_world("instance1"))
    legacy_payload.pop("timeline")
    legacy_payload.pop("relationships")
    for _key, encoded_mind in legacy_payload["character_minds"]["$mapping"]:
        encoded_mind["fields"].pop("relationship_context", None)
    legacy = service.serializer.deserialize_world(legacy_payload)
    assert legacy["timeline"] == ()
    assert legacy["relationships"] == ()

    decoded = service.load_world("instance1")
    assert decoded["timeline"][0].event_id == "history-1"
    restored = GameLauncher(action_interpreter=PlayerActionParser()).restore_saved_world(decoded)
    assert restored.executor.event_timeline.events[0].event_id == "history-1"
    assert restored.executor.relationship_manager.get_relationship("doctor", "player").trust == 65
    assert restored.executor.character_minds["doctor"].relationship_context.relationships == (
        RelationshipState("doctor", "player", trust=65, respect=10),
    )
