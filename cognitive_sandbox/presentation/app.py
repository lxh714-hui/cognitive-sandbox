from __future__ import annotations

import sys
import os
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QListWidget

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.persistence.storage.save_repository import JsonSaveRepository
from cognitive_sandbox.persistence.world_save_service import WorldSaveService
from cognitive_sandbox.application.first_launch import initialize_user_data
from cognitive_sandbox.presentation.theme import apply_theme


def _smoke_test_ui(app: QApplication, window: FoundationMainWindow) -> int:
    """Exercise the empty lobby and a visible roleplay response offscreen."""
    status = {"code": 10}
    package_ok = bool(window.scenario_registry and window.scenario_registry.list_available())

    def verify_lobby_and_roleplay() -> None:
        dialog = next(
            (widget for widget in app.topLevelWidgets()
             if isinstance(widget, QDialog) and widget.windowTitle() == "世界大厅"),
            None,
        )
        if dialog is None:
            status["code"] = 10
        else:
            lobby_list = dialog.findChild(QListWidget, "worldLibraryList")
            if window.current_session is not None or window.world_library.list_worlds():
                status["code"] = 11
            elif lobby_list is None or lobby_list.count() != 0:
                status["code"] = 12
            else:
                status["code"] = 0
                dialog.accept()

        # The smoke harness explicitly chooses a built-in scenario after verifying
        # startup did not create one implicitly.
        try:
            available = window.scenario_registry.list_available()
            if not available:
                status["code"] = 13
                window.close()
                app.quit()
                return
            window.start_new_game(available[0].scenario_id)
            window.player_input.setPlainText("观察周围")
            if not window.confirm_button.isEnabled():
                status["code"] = 15
            else:
                window.confirm_button.click()
                def verify_roleplay_result() -> None:
                    if window._is_processing:
                        QTimer.singleShot(10, verify_roleplay_result)
                        return
                    result = window.ui_runtime.last_result
                    if result is None or not result.action_executed:
                        status["code"] = 16
                    elif "你环顾四周" not in window.narrative_display.toPlainText():
                        status["code"] = 17
                    window.close()
                    app.quit()

                QTimer.singleShot(10, verify_roleplay_result)
                return
        except Exception:
            status["code"] = 14
        window.close()
        app.quit()

    window.show()
    QTimer.singleShot(0, window.open_world_lobby)
    QTimer.singleShot(250, verify_lobby_and_roleplay)
    app.exec()
    return status["code"] if package_ok else 13


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv[1:]
    if smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)
    paths = None if smoke_test else initialize_user_data()
    if paths is not None:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(paths.settings))
    window = FoundationMainWindow()
    launcher = GameLauncher()
    window.set_game_launcher(launcher)
    if not smoke_test:
        data_root = paths.savegames
        window.world_library.configure_persistence(
            WorldSaveService(JsonSaveRepository(data_root)),
            launcher.restore_saved_world,
        )
    if smoke_test:
        return _smoke_test_ui(app, window)
    window.show()
    QTimer.singleShot(0, window.open_home)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
