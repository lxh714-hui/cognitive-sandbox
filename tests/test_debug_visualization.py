from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.knowledge.models.knowledge_record import KnowledgeRecord, KnowledgeType
from cognitive_sandbox.knowledge.models.knowledge_source import KnowledgeSource
from cognitive_sandbox.knowledge.models.world_fact import WorldFact
from cognitive_sandbox.presentation.debug.debug_dashboard import DebugDashboard
from cognitive_sandbox.presentation.debug.debug_report import DebugReportBuilder
from cognitive_sandbox.presentation.debug.event_viewer import EventViewer
from cognitive_sandbox.presentation.debug.goal_inspector import GoalInspector
from cognitive_sandbox.presentation.debug.knowledge_inspector import KnowledgeInspector
from cognitive_sandbox.presentation.debug.npc_inspector import NpcInspector
from cognitive_sandbox.presentation.debug.world_inspector import WorldInspector
from cognitive_sandbox.presentation.main_window import FoundationMainWindow


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def _session():
    return GameLauncher().start_scenario("example_world")


def test_world_inspector_snapshots_world_location_resource_and_character_state(qapp):
    session = _session()
    session.executor.resource_manager.add("food", 4, location_id="clinic", resource_id="food-1")
    snapshot = WorldInspector(session).snapshot()

    assert snapshot["world_name"]
    assert snapshot["time"]
    assert snapshot["locations"]
    assert snapshot["resources"][0]["quantity"] == 4
    assert snapshot["characters"]
    with pytest.raises(TypeError):
        snapshot["world_name"] = "changed"


def test_event_npc_and_goal_inspectors_return_read_only_snapshots(qapp):
    session = _session()
    event = WorldEvent("debug-event", "main", session.executor.world_id, "npc_patrolled", "guard", {
        "description": "巡查事件",
        "parameters": {"location": "clinic"},
    }, 1, timestamp="2030-01-01T10:00:00+00:00")
    session.executor.event_pipeline.publish(event)

    events = EventViewer(session).snapshot()
    npcs = NpcInspector(session).snapshot()
    goals = GoalInspector(session).snapshot()

    assert events[0][0].event_id == "debug-event"
    assert npcs
    assert any(row["goal_type"] == "repair_clinic" for row in goals)
    with pytest.raises(TypeError):
        npcs[0]["name"] = "changed"


def test_knowledge_inspector_only_shows_records_retrieved_for_selected_character(qapp):
    session = _session()
    store = session.knowledge_store
    store.add_fact(WorldFact("known-fact", "医生看见了医疗站的灯光。", "observation", "t1"))
    store.add_knowledge(KnowledgeRecord(
        owner_id="doctor",
        fact_id="known-fact",
        knowledge_type=KnowledgeType.OBSERVED,
        source=KnowledgeSource("source-1", "visual", "医生亲眼观察"),
        confidence=0.9,
        created_at="t1",
    ))
    store.add_fact(WorldFact("hidden-fact", "地下室里藏有药品。", "secret", "t1"))

    inspector = KnowledgeInspector(session)
    entries = inspector.snapshot("doctor")

    assert [entry.fact_id for entry in entries] == ["known-fact"]
    assert "地下室" not in " ".join(entry.content for entry in entries)
    assert inspector.snapshot("survivor") == ()


def test_knowledge_inspector_rechecks_visibility_of_retriever_results(qapp):
    session = _session()
    hidden = KnowledgeRecord(
        owner_id="doctor",
        fact_id="secret-fact",
        knowledge_type=KnowledgeType.DIRECT,
        source=KnowledgeSource("secret-source", "direct", "private"),
        confidence=1.0,
        created_at="t1",
        known_content="未授权秘密",
    )

    class FaultyRetriever:
        backing_store = None

        def retrieve(self, character_id, query):
            return (hidden,)

    session.knowledge_retriever = FaultyRetriever()
    entries = KnowledgeInspector(session).snapshot("survivor")

    assert entries == ()


def test_debug_report_is_read_only_and_knowledge_is_opt_in_to_character_scope(qapp):
    session = _session()
    before = dict(session.world_state)
    report = DebugReportBuilder().build(session)
    assert "Event history" in report.text
    assert "Knowledge visible to" not in report.text
    scoped = DebugReportBuilder().build(session, character_id="doctor")
    assert "Knowledge visible to doctor" in scoped.text
    assert dict(session.world_state) == before


def test_debug_dashboard_and_window_entry_are_available_for_active_world(qapp):
    session = _session()
    dashboard = DebugDashboard(session)
    assert dashboard.tabs.count() == 11
    assert dashboard.tabs.tabText(5) == "剧情状态"
    assert dashboard.tabs.tabText(6) == "角色情绪"
    assert dashboard.tabs.tabText(7) == "导演目标"
    assert dashboard.tabs.tabText(8) == "角色权限"
    assert dashboard.tabs.tabText(9) == "角色认知"
    narrative_rows = dashboard.narrative_inspector.snapshot()
    assert narrative_rows[0][0] == "剧情压力"
    assert any(label.startswith("出场：") for label, _ in narrative_rows)
    assert dashboard.refresh().text

    window = FoundationMainWindow()
    assert not window.debug_button.isEnabled()
    window.set_game_launcher(GameLauncher())
    window._attach_roleplay_session(session)
    assert window.debug_button.isEnabled()
    dashboard.close()
    window.close()
