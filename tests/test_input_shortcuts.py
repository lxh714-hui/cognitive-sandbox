from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.main_window import FoundationMainWindow


def test_enter_uses_confirm_button_flow_and_clears_input():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    observed = {}

    class RuntimeStub:
        def handle_player_input(self, text):
            observed["input"] = text

        def handle_confirm(self):
            observed["status_visible"] = not window.response_status.isHidden()
            observed["button_disabled"] = not window.confirm_button.isEnabled()
            observed["player_message_visible"] = (
                window.message_history[-1].message_type.value == "player"
                and "帮助医生" in window.narrative_display.toPlainText()
            )

    window.set_ui_runtime(RuntimeStub())
    window.player_input.setPlainText("帮助医生")
    QTest.keyClick(window.player_input, Qt.Key.Key_Return)

    assert observed == {
        "input": "帮助医生",
        "status_visible": True,
        "button_disabled": True,
        "player_message_visible": True,
    }
    assert window.input_text == ""
    assert not window.confirm_button.isEnabled()
    assert not window.response_status.isVisible()
    window.close()
    app.processEvents()


def test_player_message_is_added_before_runtime_confirmation():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    runtime_observations = []

    class RuntimeStub:
        def handle_player_input(self, text):
            runtime_observations.append(("input", text, tuple(window.message_history)))

        def handle_confirm(self):
            runtime_observations.append(("confirm", tuple(window.message_history)))

    window.set_ui_runtime(RuntimeStub())
    window.player_input.setPlainText("保护士兵")
    window.confirm_button.click()

    assert runtime_observations[0][0:2] == ("input", "保护士兵")
    assert runtime_observations[0][2][-1].message_type.value == "player"
    assert runtime_observations[1][0] == "confirm"
    assert runtime_observations[1][1][-1].content == "保护士兵"
    displayed = window.narrative_display.toPlainText()
    assert displayed.index("你：") < displayed.index("保护士兵")
    assert "[玩家]" not in displayed
    window.close()
    app.processEvents()


def test_shift_enter_inserts_newline_without_confirming():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    confirmed: list[str] = []
    window.player_input_confirmed.connect(confirmed.append)
    window.player_input.setPlainText("第一行")
    window.player_input.setFocus()
    QTest.keyClick(window.player_input, Qt.Key.Key_End)
    QTest.keyClick(
        window.player_input,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.ShiftModifier,
    )

    assert window.input_text == "第一行\n"
    assert confirmed == []
    window.close()
    app.processEvents()
