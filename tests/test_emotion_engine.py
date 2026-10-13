from cognitive_sandbox.emotion import EmotionEngine
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.relationship.relationship_state import RelationshipState


def test_event_updates_affect_with_source_trace_and_relationship_intensity():
    engine = EmotionEngine()
    event = WorldEvent("injury-1", "main", "w", "friend_injured", "player", {}, 1,
                       target_id="npc", timestamp="day-3")
    close = engine.apply_event(event, "npc", (RelationshipState("npc", "player", trust=.8),))
    distant = engine.apply_event(event, "stranger", ())
    assert close.state.attachment == .2
    assert close.state.fear == .15
    assert distant.state.attachment == 0
    assert distant.state.fear == .05
    assert all(item.source_event_id == "injury-1" and item.timestamp == "day-3" for item in close.events)
    assert close.memories and close.memories[0].learned_tendency == "protective"


def test_relationship_change_emits_traceable_emotion_events():
    engine = EmotionEngine()
    event = WorldEvent("help-1", "main", "w", "help_attempt", "player", {}, 1, target_id="npc")
    engine.relationship_changed("npc", "player", RelationshipState("npc", "player"),
                                RelationshipState("npc", "player", trust=20), event)
    assert engine.state_for("npc").attachment > 0
    assert engine.history_for("npc")
    assert engine.history_for("npc")[0].source_event_id == "help-1"
