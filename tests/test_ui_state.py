from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.domain.llm_config import LLMConfig
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.presentation.ai_settings_panel import AISettingsPanel
from cognitive_sandbox.presentation.main_window import FoundationMainWindow


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_mode_switch_state_without_showing_window(qapp):
    window = FoundationMainWindow()
    changes: list[str] = []
    window.mode_changed.connect(changes.append)
    assert window.current_mode == "roleplay"

    window.set_mode("simulation")
    assert window.current_mode == "simulation"
    window.set_mode("director")
    assert window.current_mode == "director"
    assert changes == ["simulation", "director"]
    window.close()


def test_player_input_is_saved_when_confirmed(qapp):
    window = FoundationMainWindow()
    received: list[str] = []
    window.player_input_confirmed.connect(received.append)

    window.player_input.setPlainText("  帮助医生  ")
    assert window.confirm_button.isEnabled()
    window.confirm_player_input()

    assert window.confirmed_input == "帮助医生"
    assert received == ["帮助医生"]
    window.close()


def test_narrative_and_dialogue_are_rendered(qapp):
    window = FoundationMainWindow()
    window.append_narrative_event(
        NarrativeEvent("event-1", "一次帮助", "有人伸出了援手", ("doctor",))
    )
    window.append_dialogue_line(DialogueLine("doctor", "我来帮你。", "calm"))

    displayed = window.narrative_display.toPlainText()
    assert "一次帮助" not in displayed
    assert "有人伸出了援手" in displayed
    assert "doctor" not in displayed
    assert "我来帮你。" in displayed
    window.close()


def test_world_chronicle_entry_is_available_for_an_active_session(qapp):
    from cognitive_sandbox.application.game_launcher import GameLauncher

    window = FoundationMainWindow()
    assert window.chronicle_button.text() == "世界编年史"
    assert not window.chronicle_button.isEnabled()
    launcher = GameLauncher()
    window.set_game_launcher(launcher)
    window._attach_roleplay_session(launcher.start_scenario("example_world"))
    assert window.chronicle_button.isEnabled()
    window.close()


def test_ai_settings_panel_reads_and_generates_llm_config(qapp):
    panel = AISettingsPanel()
    panel.provider.setCurrentText("local-compatible")
    panel.model_name.setText("qwen-test")
    panel.base_url.setText("http://localhost:1234/v1/")

    config = panel.to_config(api_key="test-key")
    assert config == LLMConfig(
        api_key="test-key",
        base_url="http://localhost:1234/v1",
        model_name="qwen-test",
    )
    assert panel.provider.currentText() == "local-compatible"

    restored = AISettingsPanel()
    restored.load_config(config)
    assert restored.model_name.text() == "qwen-test"
    assert restored.base_url.text() == "http://localhost:1234/v1"
    panel.close()
    restored.close()
