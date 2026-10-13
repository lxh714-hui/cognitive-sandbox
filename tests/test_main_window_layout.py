from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings as RealQSettings, Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.service import SandboxService
from examples.sample_world import SAMPLE_AGENT, SAMPLE_MEMORIES, SAMPLE_WORLD
from cognitive_sandbox.infrastructure.ollama import DemoProvider
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore
from cognitive_sandbox.infrastructure.static_sprites import StaticSpriteRenderer
from cognitive_sandbox.presentation.main_window import MainWindow


def make_window(tmp_path, qapp, monkeypatch):
    settings_file = str(tmp_path / "settings.ini")
    settings = RealQSettings(settings_file, RealQSettings.Format.IniFormat)
    import cognitive_sandbox.presentation.main_window as main_window_module
    monkeypatch.setattr(main_window_module, "QSettings", lambda *_args: RealQSettings(settings_file, RealQSettings.Format.IniFormat))
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    service = SandboxService(store, DemoProvider())
    renderer = StaticSpriteRenderer(Path("cognitive_sandbox/assets/sprites"))
    window = MainWindow(service, SAMPLE_WORLD, SAMPLE_AGENT, SAMPLE_MEMORIES, renderer)
    window.resize(1180, 760)
    window.show()
    qapp.processEvents()
    return window, settings


def test_send_button_tracks_trimmed_input(tmp_path, qapp, monkeypatch):
    window, _settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        assert window.input.text() == ""
        assert not window.send_button.isEnabled()

        QTest.keyClicks(window.input, "   ")
        qapp.processEvents()
        assert not window.send_button.isEnabled()

        window.input.clear()
        QTest.keyClicks(window.input, "Hello")
        qapp.processEvents()
        assert window.send_button.isEnabled()

        window.input.clear()
        qapp.processEvents()
        assert not window.send_button.isEnabled()
    finally:
        window.close()


def test_button_is_centered_on_fixed_divider_and_uses_expanded_arrow(tmp_path, qapp, monkeypatch):
    window, _settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        assert window.splitter.orientation() == Qt.Orientation.Horizontal
        assert window.splitter.widget(0) is window._scene
        assert window.splitter.widget(1) is window._panel
        divider = window.splitter.mapTo(window, window.splitter.handle(1).pos())
        button_center = window._sidebar_handle._button.mapTo(window, window._sidebar_handle._button.rect().center())
        assert abs(button_center.x() - divider.x()) <= 2
        assert abs(button_center.y() - (window.splitter.mapTo(window, window.splitter.rect().topLeft()).y()
                                         + window.splitter.height() // 2)) <= 2
        assert window._sidebar_handle._button.text() == "▶"
        assert window._sidebar_handle._button.accessibleName() == "收起世界档案"
        assert window.splitter.handle(1).cursor().shape() == Qt.CursorShape.ArrowCursor
        assert abs(window.splitter.sizes()[1] / window.splitter.width() - 0.28) < 0.04
    finally:
        window.close()


def test_button_and_shortcut_toggle_sidebar_without_saving_width(tmp_path, qapp, monkeypatch):
    window, settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        transcript_before = window.transcript.toHtml()
        sprite_before = window.sprite.pixmap().cacheKey()
        QTest.mouseClick(window._sidebar_handle._button, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert window._inspector_collapsed
        assert window.splitter.sizes()[1] == 0
        assert window._sidebar_handle.isVisible()
        assert window._sidebar_handle._button.text() == "◀"
        assert window._sidebar_handle._button.accessibleName() == "展开世界档案"
        assert settings.value("sidebar/collapsed", type=bool) is True
        assert settings.value("sidebar/width") is None
        assert window.transcript.toHtml() == transcript_before
        assert window.sprite.pixmap().cacheKey() == sprite_before

        QTest.mouseClick(window._sidebar_handle._button, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert not window._inspector_collapsed
        assert abs(window.splitter.sizes()[1] / window.splitter.width() - 0.28) < 0.04
        assert settings.value("sidebar/collapsed", type=bool) is False

        window._sidebar_shortcut.activated.emit()
        qapp.processEvents()
        assert window.splitter.sizes()[1] == 0
        assert window._sidebar_handle._button.text() == "◀"
    finally:
        window.close()


def test_collapsed_state_persists_across_windows(tmp_path, qapp, monkeypatch):
    window, settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        window.toggle_sidebar()
        qapp.processEvents()
        assert settings.value("sidebar/collapsed", type=bool) is True
    finally:
        window.close()

    restored, restored_settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        qapp.processEvents()
        assert restored._inspector_collapsed
        assert restored.splitter.sizes()[1] == 0
        assert restored._sidebar_handle.isVisible()
        assert restored_settings.value("sidebar/collapsed", type=bool) is True
        restored.toggle_sidebar()
        qapp.processEvents()
        assert abs(restored.splitter.sizes()[1] / restored.splitter.width() - 0.28) < 0.04
        assert restored_settings.value("sidebar/collapsed", type=bool) is False
    finally:
        restored.close()


def test_dragging_divider_does_not_resize_sidebar(tmp_path, qapp, monkeypatch):
    window, settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        before = window.splitter.sizes()
        handle = window.splitter.handle(1)
        start = handle.rect().center()
        end = start + QPoint(45, 0)
        QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(handle, end)
        QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=end)
        qapp.processEvents()
        assert window.splitter.sizes() == before
        assert settings.value("sidebar/width") is None
    finally:
        window.close()


def test_sidebar_recalculates_on_resize_and_scene_fills_when_collapsed(tmp_path, qapp, monkeypatch):
    window, settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        window.resize(620, 480)
        qapp.processEvents()
        assert 160 <= window.splitter.sizes()[1] <= 560
        window.resize(1050, 700)
        qapp.processEvents()
        assert abs(window.splitter.sizes()[1] / window.splitter.width() - 0.28) < 0.04
        window.toggle_sidebar()
        qapp.processEvents()
        assert window.splitter.sizes()[1] == 0
        assert window.splitter.sizes()[0] >= window.splitter.width() - window.splitter.handleWidth() - 1
        assert window._sidebar_handle.isVisible()
        window.toggle_sidebar()
        qapp.processEvents()
        assert abs(window.splitter.sizes()[1] / window.splitter.width() - 0.28) < 0.04
        assert settings.value("sidebar/collapsed", type=bool) is False
    finally:
        window.close()


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_runtime_mode_switch_updates_selection_and_disables_roleplay_input(tmp_path, qapp, monkeypatch):
    from cognitive_sandbox.domain.runtime_mode import RuntimeMode

    window, _settings = make_window(tmp_path, qapp, monkeypatch)
    try:
        assert window.runtime_mode is RuntimeMode.ROLEPLAY
        assert window.roleplay_mode_button.isChecked()
        assert not window.story_mode_button.isChecked()
        assert window.input.isEnabled()

        QTest.mouseClick(window.story_mode_button, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert window.runtime_mode is RuntimeMode.STORY_SIMULATION
        assert window.story_mode_button.isChecked()
        assert not window.roleplay_mode_button.isChecked()
        assert not window.input.isEnabled()
        assert "尚未接入界面" in window.mode_status.text()

        QTest.mouseClick(window.roleplay_mode_button, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert window.runtime_mode is RuntimeMode.ROLEPLAY
        assert window.input.isEnabled()
    finally:
        window.close()
