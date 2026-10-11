from __future__ import annotations

import json

import pytest

from cognitive_sandbox.application.scenario_exporter import ScenarioExporter
from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.constraint import Constraint
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.scenario import Scenario
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.world_document import WorldDocument


def _content():
    scenario = Scenario(
        "harbor-night", "港城夜晚", "医院停电风险迫近。",
        {"danger_level": 0.4, "nested": {"lights": ["hall", "ward"]}},
        ({"id": "doctor", "name": "林夏", "role": "医生", "traits": ("compassionate",), "goals": ("救助患者",)},),
    )
    world = WorldDocument("harbor", "港城", "灾后港口城市", ("灾难爆发",), ("感染不可逆",))
    doctor = CharacterCard(
        "doctor", "林夏", 29, "女", "医生", ("compassionate",),
        "曾在医院工作。", ("救助患者",), (Constraint("hard", "不会伤害无辜者"),),
        "portraits/doctor.png",
    )
    event = EventCard(
        "hospital_power_failure", "医院停电", "备用电源即将耗尽", "initial",
        ("doctor",), ("night",), ("hospital_dark",), 1,
    )
    return ScenarioContent(scenario, world, (doctor,), (event,))


def test_export_then_package_load_round_trips_content(tmp_path):
    content = _content()
    export_path = ScenarioExporter().export(content, tmp_path / "assets" / "scenarios" / "harbor-night")

    restored = ScenarioPackageLoader().load(export_path)

    assert restored == content
    assert json.loads((export_path / "world.json").read_text(encoding="utf-8"))["world_id"] == "harbor"
    assert (export_path / "characters" / "character_0000.json").is_file()
    assert (export_path / "events" / "event_0000.json").is_file()
    assert (export_path / "scenario.json").is_file()


def test_export_does_not_modify_source_content(tmp_path):
    content = _content()
    before = (
        dict(content.scenario.initial_world_state),
        content.scenario.character_templates,
        content.world_document,
        content.character_cards,
        content.event_cards,
    )

    ScenarioExporter().export(content, tmp_path / "package")

    assert dict(content.scenario.initial_world_state) == before[0]
    assert content.scenario.character_templates == before[1]
    assert content.world_document == before[2]
    assert content.character_cards == before[3]
    assert content.event_cards == before[4]


def test_exporter_rejects_invalid_content_before_writing(tmp_path):
    content = ScenarioContent(
        _content().scenario,
        _content().world_document,
        _content().character_cards,
        (),
    )
    bad_event = object.__new__(EventCard)
    object.__setattr__(bad_event, "event_id", "")
    object.__setattr__(bad_event, "name", "bad")
    object.__setattr__(bad_event, "description", "bad")
    object.__setattr__(bad_event, "event_type", "initial")
    object.__setattr__(bad_event, "participants", ())
    object.__setattr__(bad_event, "conditions", ())
    object.__setattr__(bad_event, "effects", ())
    object.__setattr__(bad_event, "priority", 0)
    invalid = ScenarioContent(content.scenario, content.world_document, content.character_cards, (bad_event,))
    target = tmp_path / "invalid-package"

    with pytest.raises(ValueError, match="scenario content validation failed"):
        ScenarioExporter().export(invalid, target)

    assert not target.exists()
