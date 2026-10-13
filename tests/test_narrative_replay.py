import os
import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.presentation.debug.narrative_replay import NarrativeReplay


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_replay_is_character_filtered_and_hides_unowned_private_event(qapp):
    session = GameLauncher().start_anchor_world()
    visible = WorldEvent("player_note", "main", session.executor.world_id, "observe_action", "liangjing",
                        {"description": "我留意到窗边的钟慢了一分钟。"}, 0,
                        location="liangjing_home", timestamp=session.executor.world_clock.current_time().isoformat())
    hidden = WorldEvent("secret_note", "main", session.executor.world_id, "secret_event", "liuyiyi",
                        {"description": "内部隐藏记录", "visibility": "hidden"}, 0,
                        location="neighborhood", timestamp=session.executor.world_clock.current_time().isoformat())
    session.executor.event_pipeline.publish(visible)
    session.executor.event_pipeline.publish(hidden)
    replay = NarrativeReplay(session, "liangjing")
    texts = " ".join(item.text for item in replay.rows())
    assert "窗边的钟" in texts
    assert "内部隐藏记录" not in texts
    assert replay.filter.count() == 4
