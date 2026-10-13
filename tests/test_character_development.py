from cognitive_sandbox.development import DevelopmentChangeType, DevelopmentEngine
from cognitive_sandbox.domain.world_events import WorldEvent


def test_personal_experience_creates_traceable_durable_development():
    engine = DevelopmentEngine()
    event = WorldEvent("e1", "main", "w", "anomaly_observed", "liangjing",
                       {"description": "梁景亲眼看到钟表记录异常"}, 1)
    records = engine.handle_event(event)
    state = engine.get("liangjing")
    assert {item.change_type for item in records} == {
        DevelopmentChangeType.BELIEF_SHIFT,
        DevelopmentChangeType.COGNITIVE_TENDENCY,
        DevelopmentChangeType.BEHAVIOR_TENDENCY,
        DevelopmentChangeType.EMOTION_TENDENCY,
    }
    assert all(item.source_event == "e1" for item in records)
    assert dict(state.belief_shifts)["anomaly_exists"] == "anomaly_may_exist"
    assert state.tendency("behavior_tendencies", "investigate") == .05


def test_repeated_evidence_does_not_duplicate_belief_shift():
    engine = DevelopmentEngine()
    event = WorldEvent("e1", "main", "w", "anomaly_observed", "liangjing", {}, 1)
    engine.handle_event(event)
    assert engine.handle_event(event) == ()
    engine.handle_event(WorldEvent("e2", "main", "w", "anomaly_observed", "liangjing", {}, 1))
    records = engine.get("liangjing").records
    assert sum(item.change_type is DevelopmentChangeType.BELIEF_SHIFT for item in records) == 1
