from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.cognition import Belief, CognitiveMemory, CognitiveStyle, ThoughtPattern
from cognitive_sandbox.persistence.world_serializer import WorldSerializer
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata


def test_cognitive_state_round_trip_and_legacy_save_defaults():
    session = GameLauncher().start_scenario("example_world")
    engine = session.executor.cognitive_engine
    character_id = session.agent_context.character_id
    engine.styles[character_id] = CognitiveStyle(analytical=.8, suspicious=.75)
    engine.beliefs[character_id] = (Belief("fact-1", "可能存在异常", .6, .5, character_id),)
    engine.memories[character_id] = (CognitiveMemory(character_id, "event-1", "设备故障", "时间异常", "day-2"),)
    engine.thoughts[character_id] = [ThoughtPattern(character_id, "event-1", ("时间",), "时间异常", .6, ("比较时间",))]
    serializer = WorldSerializer()
    payload = serializer.serialize_world(
        SaveMetadata(session.world_instance_id, session.world_state.get("world_id", "world"),
                     "test", "test", "描述", "now", "now"), session,
    )
    restored = serializer.deserialize_world(payload)
    assert restored["cognition"]["styles"][character_id] == engine.styles[character_id]
    assert restored["cognition"]["beliefs"][character_id] == engine.beliefs[character_id]
    assert restored["cognition"]["memories"][character_id] == engine.memories[character_id]
    restored_session = GameLauncher().restore_saved_world(restored)
    assert restored_session.executor.cognitive_engine.styles[character_id] == engine.styles[character_id]

    legacy = dict(payload)
    legacy.pop("cognition")
    old_loaded = serializer.deserialize_world(legacy)
    assert old_loaded["cognition"]["styles"] == {}
    assert old_loaded["cognition"]["beliefs"] == {}
    legacy_session = GameLauncher().restore_saved_world(old_loaded)
    assert legacy_session.executor.cognitive_engine.style_for(character_id) is not None
