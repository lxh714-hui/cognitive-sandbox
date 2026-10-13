from types import SimpleNamespace

from cognitive_sandbox.cognition import AttentionProfile, CognitiveEngine
from cognitive_sandbox.application.actions.observe_handler import ObserveHandler
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from types import SimpleNamespace


def test_attention_profiles_produce_character_specific_observation_order():
    details = ("医生神情紧张", "医疗设备外壳有裂痕", "药品库存只剩一盒")
    engine = CognitiveEngine(attention_profiles={
        "social": AttentionProfile(social_signal=.95, emotional_signal=.9),
        "resource": AttentionProfile(resource_signal=.95),
    })
    social = engine.attend("social", details)
    resource = engine.attend("resource", details)
    assert social[0] == "医生神情紧张"
    assert resource[0] == "药品库存只剩一盒"


def test_observation_focus_contains_only_explicitly_visible_items():
    engine = CognitiveEngine()
    assert engine.attend("a", ("可见的桌面",)) == ("可见的桌面",)
    assert "隐藏实验室" not in engine.attend("a", ("可见的桌面",))


def test_observe_handler_records_personalized_focus_without_expanding_visibility():
    visible = ("医生神情紧张", "医疗设备外壳有裂痕", "药品库存只剩一盒")
    outputs = []
    for cid, profile in (("social", AttentionProfile(social_signal=.95, emotional_signal=.9)),
                         ("resource", AttentionProfile(resource_signal=.95))):
        context = AgentContext(cid, CharacterState(cid, cid, "居民", (), (), (), ()), (), (), {})
        engine = CognitiveEngine(attention_profiles={cid: profile})
        runtime = SimpleNamespace(
            world_state={"visible_events": visible}, agent_context=context,
            agent_contexts=(context,), turn=SimpleNamespace(turn_id=f"turn-{cid}"),
            branch_id="main", world_id="w", knowledge_store=None,
            scenario_content=None, cognitive_engine=engine,
        )
        from cognitive_sandbox.domain.action_intent import ActionIntent
        action = ActionIntent(cid, "观察", "observe")
        result = ObserveHandler().handle(action, runtime)
        outputs.append(result.narrative_events[0].description)
        assert result.narrative_events[0].description
    assert outputs[0] != outputs[1]
