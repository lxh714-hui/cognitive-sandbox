from types import SimpleNamespace

from cognitive_sandbox.application.npc.npc_decision_engine import NpcDecisionEngine
from cognitive_sandbox.cognition import CognitiveEngine, CognitiveStyle
from cognitive_sandbox.domain.character_mind import KnowledgeContext


def test_cognitive_style_changes_scoring_without_engine_authored_meaning():
    engine = CognitiveEngine(styles={
        "analyst": CognitiveStyle(analytical=.9, suspicious=.9),
        "pragmatist": CognitiveStyle(analytical=.2, suspicious=.1, pragmatic=.9),
    })
    event = SimpleNamespace(event_id="evt", event_type="异常危险", payload={"description": "异常危险"},
                            actor_id="player", target_id=None)
    visible = ("危险设备出现异常故障", "有人观察墙钟重复停在12:03")
    thoughts = [engine.interpret_event(cid, event, visible) for cid in ("analyst", "pragmatist")]
    decision = NpcDecisionEngine()
    ranked = [decision.decide_candidates(
        SimpleNamespace(identity=SimpleNamespace(character_id=cid, role="居民"), personality=SimpleNamespace(traits=(), values=())),
        KnowledgeContext(owner_id=cid), event, thought_pattern=thought, cognitive_style=engine.style_for(cid),
    ) for cid, thought in zip(("analyst", "pragmatist"), thoughts)]
    assert ranked[0][0].action_type == "investigate"
    assert ranked[1][0].action_type == "investigate"
    assert ranked[0][0].parameters["action_probability"] != ranked[1][0].parameters["action_probability"]
