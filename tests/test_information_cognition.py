from cognitive_sandbox.cognition import CognitiveEngine, CognitiveStyle, ReasoningProfile, AttentionProfile
from cognitive_sandbox.information import InformationManager
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.domain.world_events import WorldEvent


def test_only_recipient_gets_cognitive_interpretation_of_new_information():
    cognitive = CognitiveEngine(
        {"investigator": CognitiveStyle(suspicious=.9, analytical=.8)},
        {"investigator": ReasoningProfile(reasoning_depth=.8)},
        {"investigator": AttentionProfile(temporal_pattern=.9)},
    )
    manager = InformationManager(knowledge_store=KnowledgeStore(), cognitive_engine=cognitive)
    manager.handle_event(WorldEvent("e", event_type="report", actor_id="investigator",
                                    payload={"description": "有人听见午夜的异常声音"}, timestamp="t"))
    assert cognitive.thoughts["investigator"][-1].character_id == "investigator"
    assert "异常线索" in cognitive.thoughts["investigator"][-1].interpretation
    assert "other" not in cognitive.thoughts
