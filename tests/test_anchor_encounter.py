from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.character_presence import EntryRule
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.simulation_test.scenario_probe import AnchorSimulationProbe


def test_anchor_days_do_not_force_liang_and_liuyiyi_to_meet():
    reports = AnchorSimulationProbe().run(enable_player_idle=False)
    assert tuple(report.ticks for report in reports) == (1, 7, 30)
    assert all(not any({item.character_a, item.character_b} == {"liangjing", "liuyiyi"}
                       for item in report.encounters) for report in reports)


def test_anchor_contact_occurs_only_after_both_have_co_located_actions():
    session = GameLauncher().start_anchor_world()
    session.presence_manager.move_to("liangjing", "neighborhood", travel_completed=True)
    session.presence_manager.add_rule(EntryRule(
        "liuyiyi", trigger_event_types=("anomaly_detected",), allowed_locations=("neighborhood",),
    ))
    session.presence_manager.evaluate_entry("liuyiyi", event_type="anomaly_detected",
                                            current_location="neighborhood",
                                            current_time=session.executor.world_clock.current_time().isoformat())
    session.presence_manager.introduce("liuyiyi", current_location="neighborhood")
    now = session.executor.world_clock.current_time().isoformat()
    from types import SimpleNamespace
    context = SimpleNamespace(
        world_clock=session.executor.world_clock, world_state=session.world_state,
        agent_contexts=session.agent_contexts, character_minds=session.executor.character_minds,
        knowledge_retriever=session.knowledge_retriever, knowledge_store=session.knowledge_store,
        relationship_manager=session.executor.relationship_manager,
        event_timeline=session.executor.event_timeline, presence_manager=session.presence_manager,
        goal_manager=session.executor.goal_manager, motivation_manager=session.executor.motivation_manager,
        narrative_pressure=session.narrative_pressure, emotion_engine=session.emotion_engine,
        cognitive_engine=session.executor.cognitive_engine,
        resource_manager=session.executor.resource_manager, location_manager=session.executor.location_manager,
    )
    first = WorldEvent("liuyiyi-investigate", "main", session.executor.world_id,
                       "npc_investigated", "liuyiyi",
                       {"action_type": "investigate", "description": "柳依依正在调查附近线索"},
                       0, location="neighborhood", timestamp=now)
    second = WorldEvent("liangjing-observe", "main", session.executor.world_id,
                        "observe_action", "liangjing", {"description": "梁景观察周围"},
                        0, location="neighborhood", timestamp=now)
    session.executor.event_pipeline.publish(first, context=context)
    published = session.executor.event_pipeline.publish(second, context=context)
    encounters = [item for item in published if item.event_type == "social_encounter"]
    assert len(encounters) == 1
    assert session.relationship_lifecycle_manager.stage_for("liangjing", "liuyiyi").value == "ACQUAINTANCE"
    assert session.executor.relationship_manager.get_relationship("liangjing", "liuyiyi").trust == 0
    assert session.emotion_engine.state_for("liangjing").curiosity > 0
    assert session.emotion_engine.state_for("liuyiyi").curiosity > 0
    thoughts = session.executor.cognitive_engine.thoughts
    assert thoughts["liangjing"] and thoughts["liuyiyi"]
    assert thoughts["liangjing"][-1].character_id != thoughts["liuyiyi"][-1].character_id
