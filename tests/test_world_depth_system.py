from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import FrozenInstanceError

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.character_presence import EntryRule, PresenceState
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.event.event_pipeline import EventPipeline
from cognitive_sandbox.goal import CharacterGoal, GoalManager
from cognitive_sandbox.history.event_timeline import EventTimeline
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer
from cognitive_sandbox.presentation.world_chronicle import WorldChroniclePanel
from cognitive_sandbox.world_evolution import (
    EvolutionRule,
    LocationManager,
    LocationState,
    ResourceManager,
    WorldEvolutionEngine,
)


def _event(event_type, event_id="event-1", actor="doctor", payload=None, timestamp="day-1"):
    return WorldEvent(event_id, "main", "world-1", event_type, actor, payload or {}, 1, timestamp=timestamp)


def test_event_pipeline_applies_evolution_before_history_and_is_idempotent():
    timeline = EventTimeline()
    resources = ResourceManager()
    locations = LocationManager((LocationState("clinic", "医疗站", safety=10),))
    engine = WorldEvolutionEngine(resource_manager=resources, location_manager=locations)
    pipeline = EventPipeline(event_timeline=timeline, world_evolution_engine=engine)

    event = _event("npc_patrolled", payload={"parameters": {"location": "clinic"}})
    pipeline.publish(event)
    pipeline.publish(event)

    assert locations.get("clinic").safety == 15
    assert len(timeline.events) == 1
    assert engine.state_changes[0].event_id == event.event_id


def test_frozen_nested_action_parameters_are_used_for_location_evolution():
    locations = LocationManager((LocationState("clinic", "医疗站"),))
    engine = WorldEvolutionEngine(location_manager=locations)

    engine.handle_event(_event("npc_patrolled", payload={"parameters": {"location": "clinic"}}))

    assert locations.get("clinic").safety == 5


def test_resources_locations_and_goal_tree_evolve_deterministically():
    goals = GoalManager((
        CharacterGoal("doctor", "恢复医疗站", "repair_clinic", goal_id="root",
                      subgoals=("collect", "power")),
        CharacterGoal("doctor", "收集材料", "collect_materials", goal_id="collect", parent_goal_id="root"),
        CharacterGoal("doctor", "恢复供电", "restore_power", goal_id="power", parent_goal_id="root", status="paused"),
    ))
    resources = ResourceManager()
    locations = LocationManager((LocationState("clinic", "医疗站", status="damaged", power=False),))
    engine = WorldEvolutionEngine(goal_manager=goals, resource_manager=resources, location_manager=locations)

    engine.handle_event(_event("npc_materials_collected", "collect-1"))
    assert resources.quantity("medical_supplies", location_id="clinic") == 1
    assert goals.by_id("collect").progress == pytest.approx(0.2)
    assert goals.by_id("power").status == "active"

    engine.handle_event(_event("doctor_repaired_clinic", "repair-1"))
    assert resources.quantity("medical_supplies", location_id="clinic") == 0
    assert locations.get("clinic").repair_progress == 20
    assert locations.get("clinic").power is False
    assert goals.by_id("power").progress == pytest.approx(0.2)
    assert any(change.target_type == "goal" for change in engine.state_changes)


def test_location_safety_is_bounded_and_custom_resource_rules_apply():
    locations = LocationManager((LocationState("gate", "城门", safety=98),))
    resources = ResourceManager()
    engine = WorldEvolutionEngine(
        location_manager=locations,
        resource_manager=resources,
        rules=(EvolutionRule("supply_arrived", "resource", "quantity", "increment", 3, "补给到达"),),
    )

    engine.handle_event(_event("npc_patrolled", "patrol-1", payload={"location": "gate"}))
    engine.handle_event(_event("supply_arrived", "supply-1", payload={"resource_type": "food"}))

    assert locations.get("gate").safety == 100
    assert resources.quantity("food") == 3


def test_world_chronicle_is_read_only_and_shows_events_with_state_changes():
    app = QApplication.instance() or QApplication([])
    timeline = EventTimeline()
    event = _event(
        "npc_patrolled", "patrol-2",
        payload={"location": "clinic", "description": "守卫巡查了港区。"},
    )
    timeline.record_event(event)
    locations = LocationManager((LocationState("clinic", "医疗站", safety=5),))
    engine = WorldEvolutionEngine(location_manager=locations)
    engine.handle_event(event)

    panel = WorldChroniclePanel(timeline, engine.state_changes, location_manager=locations)
    assert panel.entries_list.count() == 1
    assert "守卫巡查了港区" in panel.entries_list.item(0).text()
    assert "安全度" in panel.entries_list.item(0).text()
    assert panel.entries_list.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert panel.entries_list.selectionMode() == panel.entries_list.SelectionMode.NoSelection
    panel.close()
    app.processEvents()


def test_evolution_state_round_trips_and_legacy_save_defaults_remain_valid():
    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    engine = session.executor.world_evolution_engine
    engine.handle_event(_event("npc_materials_collected", "saved-collect"))
    metadata = SaveMetadata(
        session.world_instance_id,
        session.executor.world_id,
        "example_world",
        "灰港",
        "存档兼容测试",
        "day-1",
        "day-1",
        "active",
        "running",
    )
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    decoded = serializer.deserialize_world(payload)

    assert decoded["autonomous"]["state_changes"] == engine.state_changes
    assert decoded["autonomous"]["processed_evolution_event_ids"] == ("saved-collect",)
    assert decoded["autonomous"]["resources"] == engine.resource_manager.resources
    restored = launcher.restore_saved_world(decoded)
    assert restored.executor.resource_manager.quantity("medical_supplies", location_id="clinic") == 1

    payload.pop("autonomous")
    legacy = serializer.deserialize_world(payload)
    assert legacy["autonomous"]["locations"] == ()
    assert legacy["autonomous"]["resources"] == ()


def test_state_change_and_location_models_are_immutable():
    state = LocationState("clinic", "医疗站")
    with pytest.raises(FrozenInstanceError):
        state.power = True
    change = WorldEvolutionEngine(location_manager=LocationManager((state,))).handle_event(
        _event("npc_patrolled")
    )[0]
    with pytest.raises(FrozenInstanceError):
        change.new_value = 99


def test_autonomous_ticks_progress_doctor_goal_to_powered_clinic():
    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    executor = session.executor
    session.presence_manager.add_rule(EntryRule("doctor", trigger_event_types=("doctor_arrived",), allowed_locations=("clinic",)))
    assert session.presence_manager.evaluate_entry(
        "doctor", event_type="doctor_arrived", current_location="clinic",
    ).availability is PresenceState.AVAILABLE
    session.presence_manager.introduce("doctor", current_location="clinic")
    session.presence_manager.activate("doctor")
    executor.world_clock.restore("2030-01-01T20:00:00+00:00")
    context = SimpleNamespace(
        world_clock=executor.world_clock,
        world_state=session.world_state,
        agent_contexts=session.agent_contexts,
    )
    generated = []

    for index in range(12):
        now = executor.world_clock.advance(10)
        tick = WorldEvent(
            f"depth-tick-{index}", "main", executor.world_id, "world_tick", "system", {}, index,
            timestamp=now.isoformat(),
        )
        generated.extend(executor.event_pipeline.publish(tick, context=context))

    event_types = [event.event_type for event in generated]
    assert event_types.count("npc_materials_collected") == 5
    assert event_types.count("doctor_repaired_clinic") == 5
    assert executor.location_manager.get("clinic").power is True
    assert executor.goal_manager.get("doctor", "repair_clinic").status == "completed"
    assert all(event.event_id in {record.event_id for record in executor.event_timeline.events} for event in generated)

