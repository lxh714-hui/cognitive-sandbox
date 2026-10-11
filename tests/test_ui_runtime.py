from __future__ import annotations

import os
from itertools import count

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.action_decision import ActionDecisionEngine
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
from cognitive_sandbox.presentation.ui_runtime import UIRuntime


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def make_runtime(window):
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
        ActionDecisionEngine(action_id_factory=lambda: "action-1"),
        ActionResolver(),
        ActionEventAdapter(
            world_id="world-1",
            branch_id="main",
            world_revision=1,
            event_id_factory=lambda: "event-1",
        ),
        WorldStateUpdater(),
        WorldStateApplier(),
        MemoryUpdater(memory_id_factory=lambda: "memory-1"),
        RelationshipUpdater(),
        AgentStateUpdater(),
        AgentContextBuilder(),
    )
    executor = RoleplayExecutor(PlayerActionParser(), tick, NarrativeFormatter(), DialogueGenerator())
    session = RoleplaySession(
        "player-1",
        RoleplayTurnController(turn_id_factory=lambda: "turn-1"),
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

    assert runtime.last_result.action_executed is True
    assert "一次帮助" in window.narrative_display.toPlainText()
    assert "有人伸出了援手" in window.narrative_display.toPlainText()
    assert "我只是做了应该做的事。" in window.narrative_display.toPlainText()
    assert initial_context.memories == ()
    assert runtime.session.world_state["social_trust"] == pytest.approx(0.6)
    window.close()


def test_ui_runtime_returns_narrative_and_dialogue_text(qapp):
    window = FoundationMainWindow()
    runtime, _context = make_runtime(window)
    runtime.handle_player_input("帮助医生")
    narrative, dialogue = runtime.handle_confirm()

    assert narrative == "一次帮助\n有人伸出了援手"
    assert dialogue == "我只是做了应该做的事。"
    window.close()
