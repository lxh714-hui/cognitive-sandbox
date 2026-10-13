from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.emotion import EmotionalMemory, EmotionalState
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_emotion_state_history_and_memories_round_trip_and_old_saves_default():
    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    engine = session.emotion_engine
    engine.set_state("doctor", EmotionalState(fear=.6, guilt=.3))
    world_event = WorldEvent("event1", "main", session.executor.world_id, "anomaly_detected", "player", {}, 1,
                             target_id="doctor", timestamp="day-1")
    engine.apply_event(world_event, "doctor")
    traced_history = engine.history
    memory = EmotionalMemory("event2", {"fear": .2}, "cautious", .7)
    engine.add_memory("doctor", memory)
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world",
                            "灰港", "描述", "t0", "t1")
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    decoded = serializer.deserialize_world(payload)
    assert decoded["emotion"]["states"]["doctor"] == engine.state_for("doctor")
    assert decoded["emotion"]["history"] == traced_history
    assert decoded["emotion"]["memories"] == (("doctor", engine.memories_for("doctor")[0]),
                                                   ("doctor", memory))
    restored = launcher.restore_saved_world(decoded)
    assert restored.emotion_engine.state_for("doctor") == engine.state_for("doctor")
    assert restored.emotion_engine.memories_for("doctor") == engine.memories_for("doctor")

    legacy_payload = dict(payload)
    legacy_payload.pop("emotion")
    legacy = serializer.deserialize_world(legacy_payload)["emotion"]
    assert legacy == {"states": {}, "history": (), "memories": ()}
