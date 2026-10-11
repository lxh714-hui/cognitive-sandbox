from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings

from cognitive_sandbox.application.ai_runtime_wiring import AIRuntimeWiring
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.scenario_runtime_builder import ScenarioRuntimeBuilder
from cognitive_sandbox.application.scenario_validator import ScenarioValidator
from cognitive_sandbox.application.world_validator import WorldValidator
from cognitive_sandbox.application.character_card_validator import CharacterCardValidator
from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.application.roleplay_session import RoleplaySession


PACKAGE = Path(__file__).resolve().parents[1] / "assets" / "scenarios" / "example_world"


def test_example_package_json_is_valid_and_loads_domain_content() -> None:
    json_paths = (PACKAGE / "scenario.json", PACKAGE / "world.json")
    json_paths += tuple((PACKAGE / "characters").glob("*.json"))
    json_paths += tuple((PACKAGE / "events").glob("*.json"))
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in json_paths]

    content = ScenarioPackageLoader().load(PACKAGE)

    assert all(isinstance(document, dict) for document in documents)
    assert content.scenario.scenario_id == "example_world"
    assert content.world_document.name == "灰港纪元"
    assert content.world_document.rules == (
        "资源有限，聚落需要共同维护补给与能源。",
        "人类需要合作才能应对城市中的风险。",
        "每个人掌握的信息都不完整，传闻和观察可能存在偏差。",
    )
    assert len(content.character_cards) == 3
    assert content.character_cards[0].character_id == "player"
    assert len(content.event_cards) == 2


def test_example_package_passes_validators_and_builds_runtime() -> None:
    content = ScenarioPackageLoader().load(PACKAGE)
    runtime_builder = ScenarioRuntimeBuilder()

    assert ScenarioValidator().validate(content.scenario).valid
    assert WorldValidator().validate(content.world_document).valid
    assert all(CharacterCardValidator().validate(card).valid for card in content.character_cards)
    assert all(EventCardValidator().validate(card).valid for card in content.event_cards)
    assert runtime_builder.validate(content).valid

    runtime = runtime_builder.build(content)

    assert runtime.world_state.name == "灰港纪元"
    assert runtime.world_state.state["energy_level"] == 0.2
    assert [profile.agent_id for profile in runtime.agents] == ["player", "doctor", "survivor"]
    assert {card.event_id for card in runtime.initial_events} == {
        "power_failure", "first_meeting"
    }


def test_example_world_starts_without_ai_configuration(tmp_path: Path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.clear()
    settings.sync()
    launcher = GameLauncher(ai_runtime_wiring=AIRuntimeWiring(settings=settings))

    available = launcher.scenario_loader.registry.list_available()
    session = launcher.start_scenario("example_world")

    assert any(scenario.scenario_id == "example_world" for scenario in available)
    assert isinstance(session, RoleplaySession)
    assert session.player_id == "player"
    assert session.current_turn.status == "waiting_input"
    assert session.world_state["resource_level"] == 0.35
    assert launcher.current_session is session

    session.submit_input("观察周围")
    result = session.confirm()
    assert result.action_executed
    assert result.simulation_result.events[0].event_type == "observe_action"
