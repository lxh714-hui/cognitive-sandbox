import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType


def test_dialogue_uses_character_display_name_without_debug_emotion_prefix():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher(action_interpreter=PlayerActionParser()))
    session = window.start_new_game("example_world")
    doctor = next(card for card in session.scenario_content.character_cards if card.character_id == "doctor")
    window.append_dialogue_line(DialogueLine("doctor", "这么巧？你也来了这里？", "curious"))

    message = window.message_history[-1]
    shown = window.narrative_display.toPlainText()
    assert message.message_type is MessageType.CHARACTER
    assert message.speaker_id == doctor.name
    assert doctor.name + "：" in shown
    assert "doctor" not in shown
    assert "curious" not in shown
    window.close()
