from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.emotion.emotion_engine import EmotionEngine
from cognitive_sandbox.relationship.lifecycle import RelationshipLifecycleManager
from cognitive_sandbox.relationship.relationship_manager import RelationshipManager


def test_relationship_event_uses_existing_emotion_feedback_path():
    emotion = EmotionEngine()
    relationships = RelationshipManager(emotion_engine=emotion)
    lifecycle = RelationshipLifecycleManager(relationships, character_ids=("a", "b"), emotion_engine=emotion)
    event = WorldEvent("help-1", event_type="help_attempt", actor_id="a", target_id="b", payload={})
    relationships.apply_event(event)
    lifecycle.handle_event(event)
    assert emotion.state_for("a").attachment > 0
    assert emotion.state_for("b").attachment > 0
    assert any(record.source_event_id == "help-1" for record in emotion.history)


def test_repeated_cooperation_can_adjust_only_an_existing_distrust_belief():
    from cognitive_sandbox.cognition import Belief, CognitiveEngine

    engine = CognitiveEngine(beliefs={"a": (Belief("general", "others are untrustworthy", .8, .5, "a"),)})
    relationships = RelationshipManager()
    manager = RelationshipLifecycleManager(relationships, character_ids=("a", "b"), cognitive_engine=engine)
    for index in range(3):
        event = WorldEvent(f"cooperate-{index}", event_type="cooperation", actor_id="a", target_id="b", payload={})
        relationships.apply_event(event)
        manager.handle_event(event)
    assert "\u5e76\u975e\u6240\u6709\u4eba\u90fd\u4e0d\u53ef\u4fe1" in engine.beliefs["a"][0].interpretation
    assert engine.memories["a"][-1].source_event == "cooperate-2"

