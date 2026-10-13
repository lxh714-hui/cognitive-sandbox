from pathlib import Path

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.application.scenario_registry import ScenarioRegistry


ROOT = Path(__file__).parents[1]


class RecordingLauncher(GameLauncher):
    def __init__(self, loader):
        super().__init__(scenario_loader=loader)
        self.content_builds = []

    def start_scenario_content(self, content, *, player_character_id=None):
        self.content_builds.append(content.scenario.scenario_id)
        return super().start_scenario_content(content, player_character_id=player_character_id)


def test_distinct_scenario_packages_use_the_same_start_world_path():
    loader = ScenarioLoader(registry=ScenarioRegistry())
    loader.register_package(ROOT / "assets" / "scenarios" / "anchor")
    loader.register_package(ROOT / "tests" / "fixtures" / "blank_scenario")
    launcher = RecordingLauncher(loader)

    first = launcher.start_world("anchor")
    second = launcher.start_world("blank_world")

    assert launcher.content_builds == ["anchor", "blank_world"]
    assert first.scenario_id == "anchor"
    assert second.scenario_id == "blank_world"
    assert first.world_instance_id != second.world_instance_id
    assert first.agent_contexts and second.agent_contexts
    assert not hasattr(launcher, "start_anchor_world")


def test_runtime_package_contains_no_world_named_data_or_probe_package():
    package = ROOT / "cognitive_sandbox"
    forbidden_terms = ("anchor", "harbor", "liang")
    runtime_layers = ("application", "domain", "world_evolution", "npc", "goal", "encounter", "presentation")
    matches = []
    for layer in runtime_layers:
        for path in (package / layer).rglob("*.py"):
            source = path.read_text(encoding="utf-8").casefold()
            matches.extend(f"{path.relative_to(package)}:{term}" for term in forbidden_terms if term in source)
    assert matches == []
    assert not (package / "application" / "anchor_world_loader.py").exists()
    assert not (package / "simulation_test").exists()
    assert not (package / "domain" / "sample_world.py").exists()
