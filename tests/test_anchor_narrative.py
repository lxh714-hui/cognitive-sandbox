from pathlib import Path
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.narrative.narrative_thread import NarrativeThreadStatus


def test_anchor_starts_with_non_linear_narrative_threads():
    config = ScenarioPackageLoader().load(
        Path(__file__).parents[1] / "assets" / "scenarios" / "anchor"
    ).scenario.runtime_config
    threads = {item["id"]: item for item in config["narrative_threads"]}
    assert threads["liangjing_return"]["status"] == NarrativeThreadStatus.ACTIVE.value
    assert tuple(threads["liangjing_return"]["participants"]) == ("liangjing",)
    assert threads["anomaly_investigation"]["status"] == NarrativeThreadStatus.DORMANT.value
    assert tuple(threads["anomaly_investigation"]["participants"]) == ("liuyiyi", "song")
    assert threads["potential_intersection"]["status"] == NarrativeThreadStatus.POSSIBLE.value
    assert tuple(threads["potential_intersection"]["participants"]) == ("liangjing", "liuyiyi", "pei")
