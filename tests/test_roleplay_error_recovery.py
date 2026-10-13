from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType


def test_worker_failure_is_reported_and_controls_recover():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()

    class RuntimeStub:
        def handle_player_input(self, _text):
            pass

        def execute_confirm(self):
            raise RuntimeError("provider details should stay out of the UI")

    window.set_ui_runtime(RuntimeStub())
    window.player_input.setPlainText("帮助医生")
    window.confirm_player_input()

    deadline = time.monotonic() + 3
    while window._is_processing and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()

    assert not window._is_processing
    assert window.response_status.text() == "等待行动"
    assert window.confirm_button.isEnabled() is False  # input was already cleared
    assert window.player_input.isEnabled()
    assert window.message_history[0].message_type is MessageType.PLAYER
    assert len(window.message_history) == 1
    assert window.system_message_label.text() == "行动执行失败，请重试"
    assert "provider details" not in window.narrative_display.toPlainText()
    window.close()

