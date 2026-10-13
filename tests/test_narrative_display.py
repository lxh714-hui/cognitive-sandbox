import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType


def test_narrative_is_plain_prose_without_event_title_or_internal_ids():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    window.append_narrative_event(NarrativeEvent(
        "evt-1", "关键事件标题", "雨水沿着便利店的玻璃缓缓滑落。", ("doctor_internal",),
    ))

    message = window.message_history[-1]
    shown = window.narrative_display.toPlainText()
    assert message.message_type is MessageType.NARRATION
    assert message.content == "雨水沿着便利店的玻璃缓缓滑落。"
    assert "关键事件标题" not in shown
    assert "doctor_internal" not in shown
    assert "旁白：" not in shown and "【世界】" not in shown
    window.close()
