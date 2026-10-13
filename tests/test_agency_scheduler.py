from datetime import datetime, timezone

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.simulation_test.scenario_probe import AnchorSimulationProbe
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


def test_anchor_npc_autonomously_investigates_through_executor_and_pipeline():
    session = GameLauncher().start_anchor_world()
    session.executor.world_clock.restore(datetime(2026, 1, 1, 20, tzinfo=timezone.utc).isoformat())
    AnchorSimulationProbe._configure_probe(session)
    instance = WorldInstance(session.world_instance_id, "anchor_world", session.world_instance_id,
                             "锚点", "probe", "active", "running", "d1", "liangjing")
    SimulationRunner().run(instance, session=session, tick_count=0,
                           on_start=AnchorSimulationProbe._trigger_probe_clue)
    before = session.executor.goal_manager.get("liuyiyi", "investigate_anomaly").progress
    report = SimulationRunner().run(instance, session=session, tick_count=2)
    actions = [item for item in report.events if item.event_type == "npc_investigated"]
    assert actions
    assert all(item.actor_ids == ("liuyiyi",) for item in actions)
    assert session.executor.event_timeline.events
    assert any(item.event_id in session.executor.world_evolution_engine.processed_event_ids
               for item in actions)
    assert session.executor.goal_manager.get("liuyiyi", "investigate_anomaly").progress > before
    assert session.agency_manager.snapshot().autonomous_action_history


def test_scheduler_keeps_characters_outside_story_presence_inactive():
    session = GameLauncher().start_anchor_world()
    assert session.presence_manager.get("song").availability.value == "UNKNOWN"
    assert session.presence_manager.get("pei").availability.value == "UNKNOWN"


def test_agency_inspector_shows_candidates_without_private_knowledge_dump():
    from cognitive_sandbox.presentation.debug.agency_inspector import AgencyInspector

    session = GameLauncher().start_anchor_world()
    inspection = AgencyInspector().inspect(session, "liuyiyi")
    assert inspection.current_drive == "寻找异常线索"
    assert any(item.action_type == "investigate" for item in inspection.candidates)
    assert not hasattr(inspection, "world_state")
    assert all("hidden" not in item.reason.casefold() for item in inspection.candidates)
