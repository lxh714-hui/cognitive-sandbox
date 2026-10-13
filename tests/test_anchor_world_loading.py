from pathlib import Path

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.presentation.world_lobby import WorldLobbyPanel


PACKAGE = Path(__file__).parents[1] / "assets" / "scenarios" / "anchor"


def test_scenario_package_loads_content_through_generic_package_loader():
    content = ScenarioPackageLoader().load(PACKAGE)
    assert content.world_document.name == "锚点"
    assert content.scenario.scenario_id == "anchor"
    assert {card.character_id for card in content.character_cards} == {
        "liangjing", "liuyiyi", "song", "pei"
    }
    assert {item["location_id"] for item in content.scenario.runtime_config["locations"]} == {
        "liangjing_home", "convenience_store", "neighborhood"
    }
    assert content.event_cards[0].event_type == "world_initialized"
    assert content.scenario.runtime_config["goal_transition_rules"][0]["result"] == "confirm_anomaly"


def test_generic_launcher_starts_new_instances_from_loaded_package():
    launcher = GameLauncher()
    first = launcher.start_world("anchor")
    second = launcher.start_world("anchor")
    assert first.player_id == "liangjing"
    assert first.world_instance_id != second.world_instance_id
    assert first.executor.authority_manager.player_character_id == "liangjing"
    assert len(first.agent_contexts) == 4
    assert first.scenario_id == "anchor"
    assert any(rule.result == "confirm_anomaly" for rule in first.goal_lifecycle_manager.rules)
    assert not hasattr(launcher, "start_anchor_world")


def test_lobby_lists_packages_from_registry(qapp):
    loader = ScenarioLoader()
    panel = WorldLobbyPanel(WorldLibrary(), loader.registry)
    assert panel.scenario_list.count() >= 1
    labels = [panel.scenario_list.item(index).text() for index in range(panel.scenario_list.count())]
    assert any("锚点" in label for label in labels)
    assert not hasattr(panel, "anchor_button")
    panel.close()


import os
from PySide6.QtWidgets import QApplication
import pytest


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])
