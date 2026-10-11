from __future__ import annotations

import sys
import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.scenario_selection import ScenarioSelectionPanel


def _smoke_test_ui(app: QApplication, window: FoundationMainWindow) -> int:
    """Exercise scenario startup and a visible roleplay response offscreen."""
    status = {"code": 10}

    def verify_dialog() -> None:
        dialog = next(
            (
                widget
                for widget in app.topLevelWidgets()
                if isinstance(widget, QDialog) and widget.windowTitle() == "新游戏"
            ),
            None,
        )
        panel = dialog.findChild(ScenarioSelectionPanel) if dialog is not None else None
        if dialog is None:
            status["code"] = 10
        elif panel is None:
            status["code"] = 11
        elif panel.scenario_list.count() == 0:
            status["code"] = 12
        elif panel.selected_scenario_id != "post_apocalypse_city":
            status["code"] = 13
        else:
            status["code"] = 0
            panel.start_button.click()
            if window.current_session is None or window.ui_runtime is None:
                status["code"] = 14
            else:
                window.player_input.setPlainText("观察周围")
                if not window.confirm_button.isEnabled():
                    status["code"] = 15
                else:
                    window.confirm_button.click()
                    result = window.ui_runtime.last_result
                    if result is None or not result.action_executed:
                        status["code"] = 16
                    elif "开始观察" not in window.narrative_display.toPlainText():
                        status["code"] = 17
        window.close()
        app.quit()

    window.show()
    QTimer.singleShot(0, window.open_scenario_selection)
    QTimer.singleShot(250, verify_dialog)
    app.exec()
    return status["code"]


def main() -> int:
    smoke_test = "--smoke-test" in sys.argv[1:]
    if smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    window = FoundationMainWindow()
    window.set_game_launcher(GameLauncher())
    if smoke_test:
        return _smoke_test_ui(app, window)
    window.show()
    QTimer.singleShot(0, window.open_scenario_selection)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
