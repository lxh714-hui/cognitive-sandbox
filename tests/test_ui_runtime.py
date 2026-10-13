from __future__ import annotations

import os
from itertools import count
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


def wait_for_idle(app, window, timeout=3.0):
    deadline = time.monotonic() + timeout
    while window._is_processing and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    assert not window._is_processing

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
from cognitive_sandbox.application.ai_action_interpreter import AIActionInterpreter
from cognitive_sandbox.application.action_event_adapter import ActionEventAdapter
from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_context_builder import AgentContextBuilder
from cognitive_sandbox.application.agent_state_updater import AgentStateUpdater
from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.application.memory_updater import MemoryUpdater
from cognitive_sandbox.application.narrative_formatter import NarrativeFormatter
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.application.relationship_updater import RelationshipUpdater
from cognitive_sandbox.application.roleplay_executor import RoleplayExecutor
from cognitive_sandbox.application.roleplay_session import RoleplaySession
from cognitive_sandbox.application.roleplay_turn_controller import RoleplayTurnController
from cognitive_sandbox.application.simulation_tick import SimulationTick
from cognitive_sandbox.application.world_state_applier import WorldStateApplier
from cognitive_sandbox.application.world_state_updater import WorldStateUpdater
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.agent_state import AgentDynamicState
from cognitive_sandbox.domain.character import CharacterState
from cognitive_sandbox.domain.relationship import RelationshipState
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType
from cognitive_sandbox.presentation.ui_runtime import UIRuntime


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def make_runtime(window, action_parser=None):
    turn_ids = count(1)
    action_ids = count(1)
    event_ids = count(1)
    memory_ids = count(1)
    character = CharacterState("player-1", "玩家", "医生", ("compassionate",), (), (), ())
    context = AgentContext(
        "player-1",
        character,
        (),
        (RelationshipState("player-1", "doctor", "care", 0.5),),
        {"social_trust": 0.5},
        AgentDynamicState("player-1", 0.5, 0.1, 0.6),
    )
    tick = SimulationTick(
        ActionDecisionEngine(action_id_factory=lambda: f"action-{next(action_ids)}"),
        ActionResolver(),
        ActionEventAdapter(
            world_id="world-1",
            branch_id="main",
            world_revision=1,
            event_id_factory=lambda: f"event-{next(event_ids)}",
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=lambda: f"memory-{next(memory_ids)}"),
        RelationshipUpdater(),
        AgentStateUpdater(),
        AgentContextBuilder(),
    )
    executor = RoleplayExecutor(
        action_parser or PlayerActionParser(), tick, NarrativeFormatter(), DialogueGenerator()
    )
    session = RoleplaySession(
        "player-1",
        RoleplayTurnController(turn_id_factory=lambda: f"turn-{next(turn_ids)}"),
        executor,
        context,
        {"social_trust": 0.5},
        "有人受伤",
    )
    return UIRuntime(window, session), context


def test_ui_runtime_submits_confirms_and_displays_simulation_result(qapp):
    window = FoundationMainWindow()
    runtime, initial_context = make_runtime(window)

    window.player_input.setPlainText("帮助医生")
    window.confirm_button.click()
    wait_for_idle(qapp, window)

    assert runtime.last_result.action_executed is True
    assert runtime.session.current_turn.player_input == "帮助医生"
    player_message = next(message for message in window.message_history if message.message_type is MessageType.PLAYER)
    assert player_message.content == "帮助医生"
    player_index = window.message_history.index(player_message)
    assert any(
        message.message_type is MessageType.CHARACTER
        for message in window.message_history[player_index + 1:]
    )
    assert "一次帮助" not in window.narrative_display.toPlainText()
    assert "有人伸出了援手" in window.narrative_display.toPlainText()
    assert "我只是做了应该做的事。" in window.narrative_display.toPlainText()
    assert initial_context.memories == ()
    assert runtime.session.world_state["social_trust"] == pytest.approx(0.6)
    window.close()


def test_multiple_turns_keep_player_and_world_messages_in_order(qapp):
    window = FoundationMainWindow()
    _runtime, _context = make_runtime(window)

    for text in ("帮助医生", "再次帮助医生"):
        window.player_input.setPlainText(text)
        window.confirm_button.click()
        wait_for_idle(qapp, window)

    history = window.message_history
    player_indexes = [
        index for index, message in enumerate(history)
        if message.message_type is MessageType.PLAYER
    ]
    assert len(player_indexes) == 2
    assert [history[index].content for index in player_indexes] == ["帮助医生", "再次帮助医生"]
    assert all(
        any(message.message_type is MessageType.CHARACTER for message in history[start + 1:end])
        for start, end in zip(player_indexes, player_indexes[1:] + [len(history)])
    )
    window.close()


def test_player_message_remains_when_ai_fails_and_keyword_fallback_rejects_input(qapp):
    class FailingAdapter:
        def parse_player_action(self, _text, _context):
            raise RuntimeError("simulated AI outage")

    window = FoundationMainWindow()
    runtime, _context = make_runtime(
        window,
        AIActionInterpreter(ai_adapter=FailingAdapter()),
    )

    window.player_input.setPlainText("和医生聊聊天气")
    window.confirm_button.click()
    wait_for_idle(qapp, window)

    assert runtime.last_result.action_executed is False
    player_message = next(message for message in window.message_history if message.message_type is MessageType.PLAYER)
    assert player_message.content == "和医生聊聊天气"
    assert window.system_message_label.text() == (
        "这个行动目前无法直接执行。请描述你想做什么，或者补充目标人物、地点或物品。"
    )
    displayed = window.narrative_display.toPlainText()
    assert "你：" in displayed
    assert "这个行动目前无法直接执行" not in displayed
    assert "[玩家]" not in displayed
    assert "[系统]" not in displayed
    window.close()


def test_ui_runtime_returns_narrative_and_dialogue_text(qapp):
    window = FoundationMainWindow()
    runtime, _context = make_runtime(window)
    runtime.handle_player_input("帮助医生")
    narrative, dialogue = runtime.handle_confirm()

    assert narrative == "有人伸出了援手"
    assert dialogue == "我只是做了应该做的事。"
    window.close()
