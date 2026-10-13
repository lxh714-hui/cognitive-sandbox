import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.message import MessageType


def test_message_types_render_novel_style_and_keep_status_out_of_story():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    window.append_player_message("去便利店看看")
    window.append_message(MessageType.CHARACTER, "这么巧？你也来了这里？", speaker_id="柳依依")
    window.append_message(MessageType.NARRATION, "夜色渐深，店里的灯仍亮着。")
    window.append_temporary_message("正在生成...")

    history = window.message_history
    shown = window.narrative_display.toPlainText()
    assert [item.message_type for item in history] == [
        MessageType.PLAYER, MessageType.CHARACTER, MessageType.NARRATION,
    ]
    assert "你：" in shown
    assert "柳依依：" in shown
    assert "【角色】" not in shown and "系统：" not in shown
    assert "正在生成" not in shown
    assert "正在生成..." == window.system_message_label.text()
    assert "#c5a35a" in window.narrative_display.toHtml()
    window.close()
