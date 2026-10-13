from types import SimpleNamespace

from cognitive_sandbox.cognition import AttentionProfile, CognitiveEngine, CognitiveStyle


def test_same_event_gets_different_interpretations_from_visible_information_only():
    event = SimpleNamespace(event_id="evt-clock", event_type="clock_stopped")
    engine = CognitiveEngine(
        styles={"investigator": CognitiveStyle(analytical=.9, suspicious=.9),
                "resident": CognitiveStyle(pragmatic=.9, suspicious=.1)},
        attention_profiles={"investigator": AttentionProfile(temporal_pattern=.95),
                            "resident": AttentionProfile(physical_detail=.95)},
    )
    visible = ("墙钟停在12:03", "设备外壳有磨损")
    investigator = engine.interpret_event("investigator", event, visible)
    resident = engine.interpret_event("resident", event, visible)
    assert investigator.observation_focus[0] == "墙钟停在12:03"
    assert investigator.interpretation != resident.interpretation
    assert "可能存在异常" in investigator.interpretation or "异常" in investigator.interpretation
    assert investigator.character_id == "investigator"


def test_engine_does_not_read_unprovided_world_facts():
    engine = CognitiveEngine()
    result = engine.attend("person", ("附近有一盏灯",))
    assert result == ("附近有一盏灯",)
    assert not hasattr(engine, "world_state")
