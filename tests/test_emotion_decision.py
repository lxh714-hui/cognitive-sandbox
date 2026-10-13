from cognitive_sandbox.application.npc.npc_decision_engine import NpcDecisionEngine
from cognitive_sandbox.domain.character_mind import CharacterMind, Identity, KnowledgeContext, PersonalityProfile
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.emotion import EmotionalMemory, EmotionalState


def test_emotions_softly_change_action_probability_and_enable_threshold_candidates():
    engine = NpcDecisionEngine()
    mind = CharacterMind(Identity("梁景", "resident"), PersonalityProfile())
    event = WorldEvent("anomaly", "main", "w", "anomaly_detected", "player", {"danger": "attack"}, 1)
    neutral = engine.decide_candidates(mind, KnowledgeContext(owner_id="liang"), event)
    charged_state = EmotionalState(fear=.95, guilt=.9, anger=.9, curiosity=.1, confidence=.2)
    memory = EmotionalMemory("old", {"guilt": .4}, "protective", .9)
    charged = engine.decide_candidates(mind, KnowledgeContext(owner_id="liang"), event,
                                       emotional_state=charged_state, emotional_memories=(memory,))
    assert {item.action_type for item in charged} >= {"panic_escape", "dangerous_protection", "confrontation"}
    assert charged[0].parameters["action_probability"] != neutral[0].parameters["action_probability"]
    assert abs(sum(item.parameters["action_probability"] for item in charged) - 1) < 1e-9
