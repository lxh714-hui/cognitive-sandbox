from datetime import datetime, timezone
import os

import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_instance import WorldInstance
from cognitive_sandbox.presentation.debug.simulation_replay_inspector import SimulationReplayInspector
from cognitive_sandbox.simulation_test.simulation_runner import SimulationRunner


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_replay_inspector_lists_events_in_time_order_and_does_not_mutate_session(qapp):
    session = GameLauncher().start_anchor_world()
    session.executor.world_clock.restore(datetime(2026, 1, 1, 8, tzinfo=timezone.utc).isoformat())
    instance = WorldInstance(
        session.world_instance_id, "anchor_world", session.world_instance_id,
        "锚点", "offline", "active", "running", "2026-01-01T08:00:00+00:00", "liangjing",
    )
    before_state = dict(session.world_state)
    before_threads = session.narrative_state.threads
    report = SimulationRunner().run(instance, session=session, tick_count=2)
    inspector = SimulationReplayInspector(report)
    rows = inspector.rows()
    assert len(rows) == 2
    assert rows[0].timestamp < rows[1].timestamp
    assert rows[0].event_type == "world_tick"
    assert "Day 2" in inspector.view.toPlainText()
    assert dict(session.world_state) == before_state
    assert session.narrative_state.threads == before_threads
    inspector.close()
