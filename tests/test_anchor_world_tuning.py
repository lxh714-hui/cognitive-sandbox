from pathlib import Path
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader


def test_anchor_package_loads_location_relations_routines_and_background_information():
    content = ScenarioPackageLoader().load(Path(__file__).parents[1] / "assets" / "scenarios" / "anchor")
    config = content.scenario.runtime_config
    assert config["package_version"] == "0.2"
    assert len(config["location_relations"]) >= 4
    assert all(0 <= item["information_flow"] <= 1 for item in config["location_relations"])
    assert {"liangjing", "liuyiyi", "song", "pei"} <= set(config["routines"])
    assert any(item.event_type == "neighborhood_rumor" for item in content.event_cards)
