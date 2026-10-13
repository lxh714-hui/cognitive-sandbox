from __future__ import annotations

import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.main_window import FoundationMainWindow


def _wait_for(app, predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    app.processEvents()
    return predicate()


def test_roleplay_work_runs_off_ui_thread_and_ui_remains_responsive():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    main_thread = threading.get_ident()
    worker_thread = []
    release = threading.Event()
    rendered = []

    class RuntimeStub:
        def handle_player_input(self, _text):
            pass

        def execute_confirm(self):
            worker_thread.append(threading.get_ident())
            release.wait(2)
            return object()

        def present_result(self, result):
            rendered.append(result)

    window.set_ui_runtime(RuntimeStub())
    window.player_input.setPlainText("观察周围")
    try:
        window.confirm_player_input()
        assert window._is_processing
        assert window.response_status.text() == "世界正在响应..."
        assert not window.confirm_button.isEnabled()

        timer_fired = []
        QTimer.singleShot(0, lambda: timer_fired.append(True))
        assert _wait_for(app, lambda: bool(worker_thread))
        assert _wait_for(app, lambda: bool(timer_fired))
        assert worker_thread[0] != main_thread
        assert window.input_text == ""
        assert "观察周围" in window.narrative_display.toPlainText()
    finally:
        release.set()
        assert _wait_for(app, lambda: not window._is_processing)
        window.close()

