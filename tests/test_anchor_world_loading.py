from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.world_library import WorldLibrary


def test_anchor_world_package_loads_all_configured_content():
    package = AnchorWorldLoader().load()
    assert package.world_card.genre == "psychological mystery"
    assert package.world_card.tone == "uncertain"
    assert package.scenario_content.world_document.name == "锚点"
    assert package.scenario_content.scenario.scenario_id == "anchor_world"
    assert {card.character_id for card in package.scenario_content.character_cards} == {
        "liangjing", "liuyiyi", "song", "pei"
    }
    assert {item["location_id"] for item in package.locations} == {
        "liangjing_home", "convenience_store", "neighborhood"
    }
    assert package.scenario_content.event_cards[0].event_type == "world_initialized"


def test_anchor_launcher_creates_a_fresh_world_runtime_with_all_layers():
    launcher = GameLauncher()
    first = launcher.start_anchor_world()
    second = launcher.start_anchor_world()
    assert first.player_id == "liangjing"
    assert first.world_instance_id != second.world_instance_id
    assert first.executor.authority_manager.player_character_id == "liangjing"
    assert len(first.agent_contexts) == 4
    assert first.anchor_world_package_id == "anchor_world"


def test_world_lobby_offers_anchor_world_entry(qapp):
    from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel
    panel = WorldLobbyPanel(WorldLibrary())
    assert panel.anchor_button.text() == "进入《锚点》"
    assert panel.anchor_simulation_button.text() == "观察《锚点》"
    assert "Narrative Sandbox" in panel.anchor_description.text()
    panel.close()


def pytest_configure():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import os
from PySide6.QtWidgets import QApplication
import pytest


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])
