from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType


def test_input_clears_and_player_message_is_visible_before_worker_finishes():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()

    class RuntimeStub:
        def handle_player_input(self, _text):
            pass

        def execute_confirm(self):
            time.sleep(0.15)
            return object()

        def present_result(self, _result):
            pass

    window.set_ui_runtime(RuntimeStub())
    window.player_input.setPlainText("  和医生交谈  ")
    window.confirm_player_input()

    assert window.input_text == ""
    assert window.message_history[0].message_type is MessageType.PLAYER
    assert window.message_history[0].content == "和医生交谈"
    assert len(window.message_history) == 1
    assert window.system_message_label.text() == "正在生成..."

    deadline = time.monotonic() + 2
    while window._is_processing and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert not window._is_processing
    window.close()

