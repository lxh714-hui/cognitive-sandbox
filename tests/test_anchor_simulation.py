from datetime import datetime, timezone

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.simulation_test.scenario_probe import AnchorSimulationProbe
from cognitive_sandbox.simulation_test.agency_probe import AnchorAgencyProbe
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


def _probe_session():
    session = GameLauncher().start_anchor_world()
    session.executor.world_clock.restore(datetime(2026, 1, 1, 20, tzinfo=timezone.utc).isoformat())
    AnchorSimulationProbe._configure_probe(session)
    instance = WorldInstance(
        session.world_instance_id, "anchor_world", session.world_instance_id,
        "锚点", "offline probe", "active", "running", "2026-01-01T20:00:00+00:00", "liangjing",
    )
    SimulationRunner().run(
        instance, session=session, tick_count=0,
        on_start=AnchorSimulationProbe._trigger_probe_clue,
    )
    return instance, session


def test_anchor_world_advances_ticks_and_produces_an_offline_report():
    instance, session = _probe_session()
    report = SimulationRunner().run(instance, session=session, tick_count=2, random_seed=7)
    assert report.ticks == 2
    assert (datetime.fromisoformat(report.end_time) - datetime.fromisoformat(report.start_time)).days == 2
    assert len(report.events) >= 2
    assert report.world_instance_id == instance.instance_id


def test_probe_exercises_existing_autonomous_npc_and_event_pipeline():
    instance, session = _probe_session()
    report = SimulationRunner().run(instance, session=session, tick_count=3, random_seed=9)
    assert report.characters["liuyiyi"].action_count > 0
    assert any(item.event_type == "npc_investigated" for item in report.events)
    assert session.executor.goal_manager.get("liuyiyi", "investigate_anomaly").progress > 0
    assert any(item.event_type == "anomaly_detected" for item in session.executor.event_timeline.events)
    assert report.state_changes


def test_probe_reports_knowledge_isolation_emotion_and_character_specific_cognition():
    instance, session = _probe_session()
    report = SimulationRunner().run(instance, session=session, tick_count=3, random_seed=11)
    assert report.metrics.knowledge_isolation == 1
    assert report.metrics.knowledge_leaks == 0
    assert report.metrics.emotion_dynamics > 0
    assert report.characters["liuyiyi"].emotion_changes
    interpretations = {
        cid: summary.cognition_changes[-1].interpretation
        for cid, summary in report.characters.items() if summary.cognition_changes
    }
    assert len(interpretations) >= 2
    assert len(set(interpretations.values())) > 1


def test_anchor_goal_actions_accumulate_narrative_pressure_and_candidates():
    instance, session = _probe_session()
    initial_threads = session.narrative_state.threads
    report = SimulationRunner().run(instance, session=session, tick_count=7, random_seed=13)
    assert any(item.status in {"ACTIVE", "ESCALATING"} for item in report.thread_states)
    assert report.thread_changes
    assert session.narrative_state.threads != initial_threads
    assert any(item.event_type == "thread_pressure_opportunity" for item in report.candidate_events)
    assert isinstance(report.candidate_events, tuple)


def test_director_constraint_is_reported_without_becoming_a_world_event():
    from cognitive_sandbox.director.director_intent import DirectorIntent, DirectorIntentType

    instance, session = _probe_session()
    result = session.director_manager.submit_intent(DirectorIntent(
        DirectorIntentType.CHARACTER_ENTRY, "liuyiyi", "希望柳依依较早进入当前故事"
    ))
    timeline_before = session.executor.event_timeline.events
    report = SimulationRunner().run(instance, session=session, tick_count=1, random_seed=15)
    assert result.constraint in report.director_constraints
    assert session.executor.event_timeline.events[:len(timeline_before)] == timeline_before


def test_anchor_probe_runs_day_1_day_7_and_day_30_checkpoints():
    reports = AnchorAgencyProbe().run(random_seed=17)
    assert tuple(report.ticks for report in reports) == (1, 7, 30)
    assert len({report.world_instance_id for report in reports}) == 3
    npc_action_counts = [sum(summary.action_count for cid, summary in report.characters.items()
                             if cid != "liangjing") for report in reports]
    assert npc_action_counts == sorted(npc_action_counts)
    assert npc_action_counts == [1, 7, 30]
    assert [len(report.events) for report in reports] == sorted(len(report.events) for report in reports)
    assert reports[0].characters["liuyiyi"].goal_changes
    assert reports[2].characters["liuyiyi"].goal_changes
    assert reports[2].thread_changes
    day_seven_actions = {
        event.metadata.get("action_type") for event in reports[1].events
        if event.event_type.startswith("npc_")
    }
    assert {"investigate", "organize", "observe"} <= day_seven_actions
    checkpoints = AnchorAgencyProbe.compare(reports)
    assert tuple(item.day for item in checkpoints) == (1, 7, 30)
    assert tuple(item.npc_action_count for item in checkpoints) == (1, 7, 30)
    assert tuple(item.event_count for item in checkpoints) == tuple(sorted(item.event_count for item in checkpoints))
    assert all(item.knowledge_leaks == 0 for item in checkpoints)
    # The current probe has no Liang-Jing/Liu-Yiyi encounter. Relationship
    # stages must therefore remain traceably at STRANGER instead of advancing
    # just because time passed or a separate anomaly occurred.
    for report in reports:
        pair = next(item for item in report.relationship_stages
                    if (item.character_a, item.character_b) == ("liangjing", "liuyiyi"))
        assert pair.stage.value == "STRANGER"
        assert not any((item.character_a, item.character_b) == ("liangjing", "liuyiyi")
                       for item in report.relationship_transitions)


def test_phase_10_6_anchor_probe_tracks_goal_conversion_and_personal_development():
    reports = AnchorAgencyProbe().run(random_seed=29)
    assert reports[0].characters["liangjing"].development_changes
    assert any(item.change_type.value == "belief_shift"
               for item in reports[0].characters["liangjing"].development_changes)
    assert reports[1].goal_transitions
    assert reports[1].goal_transitions[0].owner_id == "liuyiyi"
    assert reports[1].goal_transitions[0].target_goal_id == "liuyiyi:confirm_anomaly"
    assert len(reports[2].goal_transitions) == len(reports[1].goal_transitions) == 1
    assert reports[2].goal_transitions[0].target_goal_id == reports[1].goal_transitions[0].target_goal_id

