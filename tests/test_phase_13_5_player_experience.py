from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import os
import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from cognitive_sandbox.application.action_intent_parser import ActionIntentParser
from cognitive_sandbox.application.actions.generic_action_handler import GenericActionHandler
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.domain.action_intent import ActionIntent
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.validation_result import ValidationResult
from cognitive_sandbox.domain.world_document import WorldDocument
from cognitive_sandbox.domain.world_generation_result import WorldGenerationResult
from cognitive_sandbox.presentation.debug.narrative_replay import _daily_summary
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.scenario_presenter import ScenarioPresenter
from cognitive_sandbox.presentation.simulation.simulation_timeline import SimulationTimeline
from cognitive_sandbox.time.world_clock import WorldClock
from cognitive_sandbox.world_evolution.location_state import LocationManager, LocationState
from cognitive_sandbox.domain.world_events import WorldEvent


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_anchor_is_a_world_package_without_demo_product_naming():
    root = Path(__file__).resolve().parents[1]
    assert (root / "worlds" / "anchor" / "world_card.json").is_file()
    loader = (root / "cognitive_sandbox" / "application" / "anchor_world_loader.py").read_text(encoding="utf-8")
    lobby = (root / "cognitive_sandbox" / "presentation" / "world_lobby.py").read_text(encoding="utf-8")
    assert "anchor_world" in loader
    assert "进入《锚点》" in lobby


def test_world_menu_saves_and_exits_to_lobby_without_closing_window(qapp, monkeypatch):
    launcher = GameLauncher()
    session = launcher.start_anchor_world()
    window = FoundationMainWindow()
    window.show()
    window.set_game_launcher(launcher)
    window._attach_roleplay_session(session)
    session.world_state["lifecycle_probe"] = "saved"
    window.append_player_message("测试世界导航历史")
    opened = []
    monkeypatch.setattr(window, "open_world_lobby", lambda mode=None: opened.append(mode))

    window.exit_current_world()

    assert window.current_session is None
    assert launcher.current_session is None
    assert window.world_library.active_id is None
    assert window.world_library.list_worlds()[0].status == "可继续"
    assert opened == [None]
    assert window.isVisible()  # The method returns to the lobby without closing the app.
    window.switch_world(window.world_library.list_worlds()[0].instance_id)
    assert window.current_session.world_state["lifecycle_probe"] == "saved"
    assert any(message.content == "测试世界导航历史" for message in window.message_history)
    window.close()


def test_creation_dialog_has_a_return_to_lobby_control(qapp):
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher())
    dialog = window._create_ai_world_creation_dialog()
    button = dialog.findChild(QPushButton, "returnToWorldLobbyButton")
    assert button is not None
    assert button.text() == "返回世界大厅"
    dialog.close()
    window.close()


def test_player_creation_controls_select_a_player_identity(qapp):
    window = FoundationMainWindow()
    launcher = GameLauncher()
    first_character = CharacterCard("guide", "引路人", occupation="向导")
    content = ScenarioContent(
        Scenario("world", "新世界", "等待探索的世界。", {}, ()),
        WorldDocument("world", "新世界", "等待探索的世界。", (), ()),
        (first_character,),
    )
    creation = SimpleNamespace(
        generation_result=WorldGenerationResult(content, ValidationResult(True, (), ())),
        scenario_content=content,
    )
    launcher.create_world_creation_session = lambda: creation
    window.set_game_launcher(launcher)
    dialog = window._create_ai_world_creation_dialog()
    selector = dialog.findChild(type(window.mode_selector), "playerCharacterSelector")
    assert selector is not None
    assert dialog.findChild(QPushButton, "createPlayerCharacterButton").text() == "创建玩家角色"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("cognitive_sandbox.presentation.main_window.QInputDialog.getText", lambda *args: ("新玩家", True))
    dialog.findChild(QPushButton, "createPlayerCharacterButton").click()
    assert selector.currentText() == "新玩家"
    assert creation.scenario_content.character_cards[-1].name == "新玩家"
    assert selector.currentData() == creation.scenario_content.character_cards[-1].character_id
    monkeypatch.undo()
    dialog.close()
    window.close()


def test_narrative_rendering_uses_natural_text_without_debug_tags(qapp):
    window = FoundationMainWindow()
    window.append_narrative_event(
        NarrativeEvent("evt", "行动", "你走进街角。", ())
    )
    window.append_system_message("暂时无法理解你的行动。请补充目标人物或地点。")
    text = window.narrative_display.toPlainText()
    assert "你走进街角。" in text
    assert "暂时无法理解你的行动" not in text
    assert window.system_message_label.text() == "暂时无法理解你的行动。请补充目标人物或地点。"
    assert "[角色/世界" not in text
    assert "[系统]" not in text
    window.close()


def test_generic_actions_advance_world_time_and_update_known_location():
    start = datetime(2030, 1, 1, 8, tzinfo=timezone.utc)
    clock = WorldClock(start)
    locations = LocationManager((
        LocationState("home", "梁景住所", tags=("home",)),
        LocationState("store", "街角便利店"),
    ), current_location_id="home")
    turn = RoleplayTurn("turn", "player", "executing", "去街角便利店")
    context = SimpleNamespace(
        world_state={"location": "梁景住所"},
        presence_manager=None,
        location_manager=locations,
        world_clock=clock,
        branch_id="main",
        world_id="world",
        agent_context=AgentContext("player", CharacterState("player", "玩家", "居民", (), (), (), ()), (), (), {}),
        agent_contexts=(),
        turn=turn,
    )
    action = ActionIntent("player", "去街角便利店", "move", object="街角便利店")

    result = GenericActionHandler(id_factory=lambda: "id").handle(action, context)

    assert result.action_executed
    assert result.simulation_result.world_state["location"] == "街角便利店"
    assert clock.current_time() > start
    assert result.simulation_result.events[0].event_type == "player_traveled"


def test_unknown_inspect_target_gets_safe_player_facing_message():
    turn = RoleplayTurn("turn", "player", "executing", "查看地下实验室")
    context = SimpleNamespace(
        world_state={}, presence_manager=None, location_manager=None, world_clock=None,
        branch_id="main", world_id="world", agent_context=SimpleNamespace(character_id="player"),
        agent_contexts=(), turn=turn,
    )
    result = GenericActionHandler().handle(
        ActionIntent("player", "查看地下实验室", "inspect", object="地下实验室"), context
    )
    assert not result.action_executed
    assert "目前还无法确认" in result.system_message
    assert "must not be empty" not in result.system_message


def test_daily_story_summary_groups_meaningful_categories():
    from cognitive_sandbox.presentation.debug.narrative_replay import NarrativeReplayEntry
    rows = (
        NarrativeReplayEntry("2030-01-01T09:00:00+00:00", 1, "柳依依发现一条线索。", category="线索与调查"),
        NarrativeReplayEntry("2030-01-01T10:00:00+00:00", 1, "梁景与柳依依开始合作。", category="关系与接触"),
    )
    summary = _daily_summary(rows)
    assert "Day 1 摘要" in summary
    assert "线索与调查" in summary
    assert "关系与接触" in summary
    assert "值得留意" not in summary


def test_story_timeline_hides_routine_and_empty_generic_events(qapp):
    timeline = SimulationTimeline()
    start = "2030-01-01T08:00:00+00:00"
    events = (
        WorldEvent("routine", "main", "world", "npc_worked", "pei",
                   {"description": "裴照常上班。"}, 0,
                   timestamp="2030-01-01T09:00:00+00:00"),
        WorldEvent("clue", "main", "world", "npc_investigated", "liuyiyi",
                   {"description": "柳依依发现一条线索。"}, 0,
                   timestamp="2030-01-02T09:00:00+00:00", metadata={"importance_level": 2}),
        WorldEvent("empty", "main", "world", "unclassified", "pei", {}, 0,
                   timestamp="2030-01-02T10:00:00+00:00"),
    )
    timeline.set_events(events, start_time=start)
    shown = [timeline.item(index).text() for index in range(timeline.count())]
    assert len(shown) == 1
    assert "Day 2 09:00" in shown[0]
    assert "线索与调查" in shown[0]
    assert "裴照常上班" not in shown[0]
    assert "值得留意" not in shown[0]


def test_player_action_parser_recognizes_common_everyday_actions():
    parser = ActionIntentParser()
    assert parser.parse("player", "我起床了").intent == "wake"
    assert parser.parse("player", "我吃点东西").intent == "eat"
    assert parser.parse("player", "我去上班").intent == "work"
    assert parser.parse("player", "我回家").intent == "go_home"
    assert parser.parse("player", "去街角便利店").object == "街角便利店"
    assert parser.parse("player", "找柳依依").intent == "find"
    assert parser.parse("player", "查看建筑").intent == "inspect"


def test_scenario_opening_is_grounded_in_world_and_player(qapp):
    session = GameLauncher().start_anchor_world()
    opening = ScenarioPresenter().opening(session)
    assert "锚点" in opening
    assert "梁景" in opening
    assert "异常" in opening or "城市" in opening or "生活" in opening
    assert "None" not in opening
    assert "liangjing" not in opening
