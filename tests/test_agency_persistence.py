from datetime import datetime, timezone

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer
from cognitive_sandbox.simulation_test.scenario_probe import AnchorSimulationProbe
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


def test_agency_state_and_action_history_restore_from_save():
    launcher = GameLauncher()
    session = launcher.start_anchor_world()
    session.executor.world_clock.restore(datetime(2026, 1, 1, 20, tzinfo=timezone.utc).isoformat())
    AnchorSimulationProbe._configure_probe(session)
    instance = WorldInstance(session.world_instance_id, "anchor_world", session.world_instance_id,
                             "锚点", "probe", "active", "running", "d1", "liangjing")
    SimulationRunner().run(instance, session=session, tick_count=0,
                           on_start=AnchorSimulationProbe._trigger_probe_clue)
    SimulationRunner().run(instance, session=session, tick_count=2)
    session.agency_manager.record_routine("probe:routine")
    expected = session.agency_manager.snapshot()
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "anchor_world",
                            "锚点", "probe", "d1", "d2", "active", "running")
    serializer = WorldSerializer()
    decoded = serializer.deserialize_world(serializer.serialize_world(metadata, session))
    assert decoded["autonomous"]["agency_state"] == expected
    assert decoded["autonomous"]["agency_state"].routine_progress["probe:routine"] == 1
    assert decoded["autonomous"]["agency_state"].autonomous_action_history
    restored = launcher.restore_saved_world(decoded)
    assert restored.agency_manager.snapshot() == expected


def test_legacy_autonomous_save_defaults_to_empty_agency_state():
    from cognitive_sandbox.agency.agency_state import AgencyState

    session = GameLauncher().start_scenario("example_world")
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world",
                            "world", "desc", "d1", "d1", "active", "running")
    payload = WorldSerializer().serialize_world(metadata, session)
    payload.pop("autonomous")
    decoded = WorldSerializer().deserialize_world(payload)
    assert isinstance(decoded["autonomous"]["agency_state"], AgencyState)
