import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QListWidget

from cognitive_sandbox.presentation.home.home_page import HomePage


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def test_home_exposes_world_modes_recent_list_and_separate_debug_entry(qapp):
    home = HomePage()
    assert home.findChild(QListWidget, "homeRecentWorlds") is not None
    assert home.enterWorldButton.text() == "进入世界"
    assert home.observeSimulationButton.text() == "观察模拟"
    assert home.directorModeButton.text() == "导演模式"
    assert home.developer_button.text() == "开发者诊断"
    home.close()
