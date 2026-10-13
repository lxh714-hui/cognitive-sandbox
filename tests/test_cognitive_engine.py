from types import SimpleNamespace

from cognitive_sandbox.cognition import AttentionProfile, CognitiveEngine


def test_scenario_rules_shape_attention_and_interpretation_without_engine_semantics():
    event = SimpleNamespace(event_id="evt", event_type="signal")
    rule = {
        "pattern": "clock",
        "category": "temporal_pattern",
        "interpretation": "The visible detail may warrant checking.",
        "confidence": .7,
    }
    engine = CognitiveEngine(
        attention_profiles={"observer": AttentionProfile(temporal_pattern=.95)}, rules=(rule,),
    )
    result = engine.interpret_event("observer", event, ("clock detail", "worn casing"))
    assert result.observation_focus[0] == "clock detail"
    assert result.interpretation == rule["interpretation"]
    assert result.confidence > rule["confidence"]


def test_engine_does_not_read_unprovided_world_facts():
    engine = CognitiveEngine()
    result = engine.attend("person", ("a visible object",))
    assert result == ("a visible object",)
    assert not hasattr(engine, "world_state")
