from __future__ import annotations

import json

import pytest

from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.domain.scenario_content import ScenarioContent


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _package(root):
    _write(
        root / "scenario.json",
        {
            "scenario_id": "harbor-night",
            "name": "港城夜晚",
            "description": "医院停电风险迫近。",
            "initial_world_state": {"danger_level": 0.4},
            "character_templates": [
                {"id": "doctor", "name": "林夏", "role": "医生", "traits": ["compassionate"], "goals": ["救助患者"]}
            ],
            "runtime_config": {
                "entity_aliases": {"医生": "doctor"},
                "action_durations": {"work": 42},
            },
        },
    )
    _write(
        root / "world.json",
        {"world_id": "harbor", "name": "港城", "description": "灾后港口城市", "history": [], "rules": ["感染不可逆"]},
    )
    _write(
        root / "characters" / "character_0000.json",
        {
            "character_id": "doctor", "name": "林夏",
            "identity": {"age": 29, "gender": "女", "occupation": "医生"},
            "personality": ["compassionate"], "background": "曾在医院工作。",
            "goals": ["救助患者"], "constraints": [{"type": "hard", "content": "不会伤害无辜者"}],
        },
    )
    _write(
        root / "events" / "event_0000.json",
        {
            "event_id": "hospital_power_failure", "name": "医院停电",
            "description": "备用电源即将耗尽", "event_type": "initial",
            "participants": ["doctor"], "conditions": ["night"],
            "effects": ["hospital_dark"], "priority": 1,
        },
    )
    return root


def test_package_loader_reads_complete_content_bundle_and_does_not_edit_files(tmp_path):
    root = _package(tmp_path / "package")
    files_before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*.json")}

    content = ScenarioPackageLoader().load(root)

    assert isinstance(content, ScenarioContent)
    assert content.scenario.scenario_id == "harbor-night"
    assert content.world_document.world_id == "harbor"
    assert [card.character_id for card in content.character_cards] == ["doctor"]
    assert [card.event_id for card in content.event_cards] == ["hospital_power_failure"]
    assert content.scenario.runtime_config["entity_aliases"]["医生"] == "doctor"
    assert content.scenario.runtime_config["action_durations"]["work"] == 42
    assert {path.relative_to(root): path.read_bytes() for path in root.rglob("*.json")} == files_before


def test_package_loader_rejects_invalid_nested_card_instead_of_returning_partial_content(tmp_path):
    root = _package(tmp_path / "package")
    event_path = root / "events" / "event_0000.json"
    event_data = json.loads(event_path.read_text(encoding="utf-8"))
    event_data["priority"] = -1
    _write(event_path, event_data)

    with pytest.raises(ValueError, match="priority"):
        ScenarioPackageLoader().load(root)


def test_package_loader_requires_scenario_metadata_and_world_document(tmp_path):
    package = tmp_path / "empty"
    package.mkdir()
    with pytest.raises(ValueError, match="scenario JSON file not found"):
        ScenarioPackageLoader().load(package)

    root = _package(tmp_path / "missing-world")
    (root / "world.json").unlink()
    with pytest.raises(ValueError, match="world JSON file not found"):
        ScenarioPackageLoader().load(root)
