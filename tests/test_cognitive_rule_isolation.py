from types import SimpleNamespace

from cognitive_sandbox.cognition import CognitiveEngine
from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime
from cognitive_sandbox.domain.world_state import WorldState


TEXT = "墙上的钟显示12:03"
EVENT = SimpleNamespace(event_id="event-1", event_type="observation")


def _runtime(scenario_id, rules=()):
    return ScenarioRuntime(
        scenario_id=scenario_id,
        world_state=WorldState(f"world-{scenario_id}", scenario_id, {}),
        agents=(), initial_events=(), cognitive_rules=rules,
    )


def test_empty_runtime_does_not_assign_meaning_to_clock_text():
    runtime = _runtime("blank")
    engine = CognitiveEngine(rules=runtime.cognitive_rules)

    result = engine.interpret_event("observer", EVENT, (TEXT,))

    assert runtime.cognitive_rules == ()
    assert result.interpretation == "目前提供的信息不足以形成场景解释。"
    assert "异常" not in result.interpretation


def test_runtime_rule_interprets_same_text_using_package_authored_meaning():
    expected = "该时间读数与本场景中的既有模式不一致。"
    runtime = _runtime("clock-world", ({
        "pattern": "12:03",
        "category": "temporal_pattern",
        "interpretation": expected,
        "confidence": .8,
    },))
    engine = CognitiveEngine(rules=runtime.cognitive_rules)

    result = engine.interpret_event("observer", EVENT, (TEXT,))

    assert result.interpretation == expected


def test_simultaneous_scenarios_keep_cognitive_rules_isolated():
    first = _runtime("first", ({
        "pattern": "12:03", "category": "temporal_pattern",
        "interpretation": "Interpretation from first package.",
    },))
    second = _runtime("second", ({
        "pattern": "12:03", "category": "temporal_pattern",
        "interpretation": "Interpretation from second package.",
    },))
    first_engine = CognitiveEngine(rules=first.cognitive_rules)
    second_engine = CognitiveEngine(rules=second.cognitive_rules)

    first_result = first_engine.interpret_event("observer", EVENT, (TEXT,))
    second_result = second_engine.interpret_event("observer", EVENT, (TEXT,))
    empty_result = CognitiveEngine().interpret_event("observer", EVENT, (TEXT,))

    assert first_result.interpretation == "Interpretation from first package."
    assert second_result.interpretation == "Interpretation from second package."
    assert empty_result.interpretation == "目前提供的信息不足以形成场景解释。"
