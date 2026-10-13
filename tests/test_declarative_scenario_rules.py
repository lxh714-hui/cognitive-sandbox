from __future__ import annotations

import json

import pytest

from cognitive_sandbox.application.scenario_package_loader import ScenarioPackageLoader
from cognitive_sandbox.application.scenario_rule_resolver import ScenarioRuleResolver
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.world_evolution import LocationManager, LocationState, WorldEvolutionEngine


def _package(root, scenario_id, location_id, rule):
    root.mkdir(parents=True, exist_ok=True)
    (root / "world.json").write_text(json.dumps({
        "world_id": scenario_id, "name": scenario_id, "description": "test world",
        "history": [], "rules": [],
    }), encoding="utf-8")
    (root / "scenario.json").write_text(json.dumps({
        "scenario_id": scenario_id,
        "name": scenario_id,
        "description": "isolated test scenario",
        "initial_world_state": {"location": location_id},
        "character_templates": [{"id": "worker", "name": "Worker", "goals": []}],
        "runtime_config": {
            "locations": [{"location_id": location_id, "name": location_id, "safety": 1}],
            "evolution_rules": [rule],
        },
    }), encoding="utf-8")


def _rule(target_id):
    return {
        "event_type": "machine_checked",
        "when": [],
        "effects": [{
            "type": "modify_value",
            "target": {"type": "location", "id": target_id},
            "field": "safety",
            "delta": 2,
            "reason": "scenario-defined generic effect",
        }],
    }


def _event(event_type, event_id, location, actor="worker"):
    return WorldEvent(event_id, "main", "world", event_type, actor, {}, 1,
                      location=location, timestamp="day-1")


def _run(content, event, resolver=None):
    configured_locations = content.scenario.runtime_config["locations"]
    manager = LocationManager(tuple(
        LocationState(item["location_id"], item["name"], safety=item.get("safety", 0))
        for item in configured_locations
    ))
    engine = WorldEvolutionEngine(
        location_manager=manager,
        rule_resolver=resolver or ScenarioRuleResolver(content.scenario.runtime_config["evolution_rules"]),
    )
    changes = engine.handle_event(event)
    return engine, manager, changes


def test_generic_factory_package_loads_and_applies_world_delta(tmp_path):
    package = tmp_path / "factory_world"
    _package(package, "factory_world", "factory_floor", _rule("factory_floor"))

    content = ScenarioPackageLoader().load(package)
    engine, locations, changes = _run(content, _event("machine_checked", "check-1", "factory_floor"))

    assert locations.get("factory_floor").safety == 3
    assert len(changes) == 1
    assert changes[0].target_type == "location"
    assert engine.processed_event_ids == ("check-1",)


def test_anchor_and_space_station_use_the_same_loader_and_evolution_path(tmp_path):
    loader = ScenarioPackageLoader()
    anchor = loader.load("assets/scenarios/anchor")
    station_dir = tmp_path / "space_station"
    _package(station_dir, "space_station", "orbital_deck", _rule("orbital_deck"))
    station = loader.load(station_dir)

    # Feed identical declared behavior through one resolver instance and the
    # same engine construction path. Only package locations differ.
    shared_resolver = ScenarioRuleResolver((_rule("$event_location"),))
    anchor_engine, anchor_locations, anchor_changes = _run(
        anchor, _event("machine_checked", "anchor-event", "liangjing_home"), shared_resolver
    )
    station_engine, station_locations, station_changes = _run(
        station, _event("machine_checked", "station-event", "orbital_deck"), shared_resolver
    )

    assert anchor_changes and anchor_locations.get("liangjing_home").safety == pytest.approx(2.55)
    assert station_changes and station_locations.get("orbital_deck").safety == 3
    assert type(anchor_engine) is type(station_engine) is WorldEvolutionEngine


def test_unknown_primitive_and_unknown_target_are_rejected_at_package_load(tmp_path):
    package = tmp_path / "invalid"
    bad = _rule("factory_floor")
    bad["effects"][0] = {"type": "repair_clinic"}
    _package(package, "invalid", "factory_floor", bad)

    with pytest.raises(ValueError, match="registered rule primitive"):
        ScenarioPackageLoader().load(package)

    bad["effects"][0] = {
        "type": "set_state", "target": {"type": "location", "id": "missing"},
        "field": "safety", "value": 1,
    }
    _package(package, "invalid", "factory_floor", bad)
    with pytest.raises(ValueError, match="unknown location"):
        ScenarioPackageLoader().load(package)


def test_script_like_rule_data_is_rejected(tmp_path):
    package = tmp_path / "scripted"
    bad = _rule("factory_floor")
    bad["effects"][0]["callback"] = "evaluate(payload)"
    _package(package, "scripted", "factory_floor", bad)

    with pytest.raises(ValueError, match="executable content"):
        ScenarioPackageLoader().load(package)


def test_pending_event_and_opportunity_effects_only_create_deltas():
    rules = ({
        "event_type": "source_event",
        "effects": [
            {"type": "create_event", "event_type": "candidate_event", "payload": {"value": 1}},
            {"type": "create_opportunity", "template": {"opportunity_id": "candidate", "description": "Possible"}},
        ],
    },)
    engine = WorldEvolutionEngine(rule_resolver=ScenarioRuleResolver(rules))
    changes = engine.handle_event(_event("source_event", "source-1", "nowhere"))

    assert len(changes) == 2
    assert len(engine.pending_events) == 1
    assert engine.pending_events[0]["event_type"] == "candidate_event"
    assert len(engine.pending_opportunities) == 1
    assert engine.pending_opportunities[0]["opportunity_id"] == "candidate"


def test_entity_state_and_relationship_use_generic_delta_storage():
    resolver = ScenarioRuleResolver(({
        "event_type": "machine_checked",
        "effects": [
            {"type": "set_state", "target": {"type": "entity", "id": "worker"},
             "field": "readiness", "value": "ready"},
            {"type": "modify_relationship", "source": "worker", "target": "worker",
             "field": "trust", "delta": 0.25},
        ],
    },))
    engine = WorldEvolutionEngine(rule_resolver=resolver)

    changes = engine.handle_event(_event("machine_checked", "entity-1", "factory_floor"))

    assert [change.target_type for change in changes] == ["entity", "relationship"]
    assert engine.state_values[("entity", "worker", "readiness")] == "ready"
    assert engine.relationship_values[("worker->worker", "trust")] == pytest.approx(0.25)
