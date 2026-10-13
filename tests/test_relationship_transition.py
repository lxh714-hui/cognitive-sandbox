from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.relationship.lifecycle import RelationshipLifecycleManager, RelationshipStage
from cognitive_sandbox.relationship.relationship_manager import RelationshipManager


def test_repeated_cooperation_advances_stages_with_source_trace():
    core = RelationshipManager()
    manager = RelationshipLifecycleManager(core, character_ids=("a", "b"))
    assert manager.stage_for("a", "b") is RelationshipStage.STRANGER
    for index in range(1, 4):
        event = WorldEvent(
            f"coop-{index}", event_type="cooperation", actor_id="a", target_id="b",
            payload={}, world_revision=index,
        )
        manager.handle_event(event)
    assert manager.stage_for("a", "b") is RelationshipStage.COOPERATIVE
    assert manager.stage_for("b", "a") is RelationshipStage.COOPERATIVE
    assert manager.transitions[-1].source_event_id == "coop-3"


def test_ordinary_dialogue_does_not_claim_information_was_shared():
    manager = RelationshipLifecycleManager(RelationshipManager(), character_ids=("a", "b"))
    event = WorldEvent("talk", event_type="dialogue_event", actor_id="a", target_id="b", payload={})
    manager.handle_event(event)
    assert manager.stage_for("a", "b") is RelationshipStage.ACQUAINTANCE
    assert manager.memories[0].memory_type == "observe"


def test_roleplay_event_pipeline_records_relationship_lifecycle_automatically():
    from cognitive_sandbox.application.game_launcher import GameLauncher
    from cognitive_sandbox.application.player_action_parser import PlayerActionParser

    session = GameLauncher(action_interpreter=PlayerActionParser()).start_scenario("example_world")
    other = next(item.character_id for item in session.agent_contexts if item.character_id != session.player_id)
    event = WorldEvent("pipeline-talk", event_type="dialogue_event", actor_id=session.player_id,
                       target_id=other, payload={})
    session.executor.event_pipeline.publish(event)
    assert any(item.source_event_id == "pipeline-talk"
               for item in session.relationship_lifecycle_manager.events)

