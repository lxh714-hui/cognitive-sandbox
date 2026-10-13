from pathlib import Path
import shutil

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.domain.scenario_runtime import ScenarioRuntime
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.domain.world_state import WorldState
from cognitive_sandbox.application.scenario_rule_resolver import ScenarioRuleResolver
from cognitive_sandbox.history.world_memory import WorldMemory
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


ROOT = Path(__file__).parents[1]
BLANK_PACKAGE = Path(__file__).parent / "fixtures" / "blank_scenario"


def _start(package_root, scenario_id):
    loader = ScenarioLoader(package_root=package_root)
    launcher = GameLauncher(scenario_loader=loader)
    session = launcher.start_world(scenario_id)
    return launcher, session


def test_distinct_packages_enter_the_same_runtime_and_pipeline_path():
    anchor_launcher, anchor_session = _start(ROOT / "assets" / "scenarios", "anchor")
    blank_launcher, blank_session = _start(BLANK_PACKAGE.parent, "blank_world")

    for launcher, session in ((anchor_launcher, anchor_session), (blank_launcher, blank_session)):
        runtime = session.executor.world_evolution_engine.scenario_runtime
        assert isinstance(runtime, ScenarioRuntime)
        assert type(runtime) is ScenarioRuntime
        assert session.scenario_runtime.scenario_id == runtime.scenario_id
        assert session.scenario_runtime.configuration == runtime.configuration
        assert type(session.executor.event_pipeline) is type(anchor_session.executor.event_pipeline)
        assert session.executor.event_pipeline.world_evolution_engine is session.executor.world_evolution_engine


def test_runtime_carries_package_configuration_and_content_as_immutable_injection():
    _launcher, session = _start(ROOT / "assets" / "scenarios", "anchor")
    runtime = session.scenario_runtime

    assert runtime.configuration
    assert runtime.character_cards
    assert runtime.world_document is not None
    assert runtime.initial_events
    assert runtime.world_document.world_id == session.world_instance_id
    try:
        runtime.configuration["locations"] = ()
        assert False, "runtime configuration must be immutable"
    except TypeError:
        pass


def test_world_memory_uses_one_neutral_record_schema_for_distinct_events():
    memory = WorldMemory()
    events = (
        WorldEvent("e-a", event_type="signal_received", actor_id="entity-a", target_id="place-a",
                   payload={"description": "private narrative text", "custom_world_field": "secret-a"}),
        WorldEvent("e-b", event_type="machine_stopped", actor_id="entity-b", target_id="place-b",
                   payload={"description": "another story", "other_private_field": {"x": 2}}),
    )
    for event in events:
        memory.record_event(event)

    records = memory.history.event_history
    deltas = memory.event_deltas
    assert len(records) == len(deltas) == 2
    assert all(record.summary == "Event applied" for record in records)
    assert all(set(record.metadata) == {"event_type", "actor_id", "target_id", "location"} for record in records)
    assert all(delta.change_type == "event_applied" for delta in deltas)
    assert all(delta.after == {"type": event.event_type} for delta, event in zip(deltas, events))
    assert "private narrative text" not in repr(memory.snapshot())
    assert "custom_world_field" not in repr(memory.snapshot())


def test_event_pipeline_dispatches_different_package_events_uniformly():
    from cognitive_sandbox.event.event_pipeline import EventPipeline

    received = []
    pipeline = EventPipeline()
    pipeline.subscribe(lambda event, context: received.append((event.type, event.source)), name="observer")
    first = WorldEvent("event-1", event_type="signal_received", actor_id="entity-a", payload={})
    second = WorldEvent("event-2", event_type="machine_stopped", actor_id="entity-b", payload={})

    assert pipeline.publish(first) == (first,)
    assert pipeline.publish(second) == (second,)
    assert received == [("signal_received", "entity-a"), ("machine_stopped", "entity-b")]


def test_applied_world_delta_is_recorded_as_a_neutral_memory_change():
    from cognitive_sandbox.event.event_pipeline import EventPipeline
    from cognitive_sandbox.world_evolution.world_evolution_engine import WorldEvolutionEngine

    runtime = ScenarioRuntime(
        "runtime", WorldState("w", "World", {}), (), (),
        entities=({"id": "entity-a", "kind": "entity"},),
        rules=({"event_type": "signal_received", "effects": ({
            "type": "set_state", "target": {"type": "entity", "id": "entity-a"},
            "field": "active", "value": True,
        },)},),
    )
    memory = WorldMemory()
    engine = WorldEvolutionEngine(
        rule_resolver=ScenarioRuleResolver.from_runtime(runtime), scenario_runtime=runtime,
    )
    pipeline = EventPipeline(world_evolution_engine=engine, world_memory=memory)
    event = WorldEvent("state-event", event_type="signal_received", actor_id="entity-a")

    pipeline.publish(event)

    change = next(item for item in memory.event_deltas if item.change_type == "state_change")
    assert (change.target, change.field, change.before, change.after) == (
        "entity-a", "active", None, True,
    )
    assert change.cause == "state changed by event"


def test_removing_package_does_not_prevent_restore_of_saved_runtime(tmp_path):
    packages = tmp_path / "packages"
    packages.mkdir()
    package_copy = packages / "detached_world"
    shutil.copytree(BLANK_PACKAGE, package_copy)
    launcher, session = _start(packages, "blank_world")
    metadata = SaveMetadata(
        session.world_instance_id, session.world_state.get("world_id", "world"),
        "blank_world", "Blank", "Package-independent snapshot", "day-1", "day-1",
        player_character_id=session.player_id,
    )
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    saved = serializer.deserialize_world(payload)

    shutil.rmtree(package_copy)
    empty_loader = ScenarioLoader(package_root=packages)
    assert empty_loader.load("blank_world") is None
    restored = GameLauncher(scenario_loader=empty_loader).restore_saved_world(saved)
    assert restored.world_state == session.world_state
    assert isinstance(restored.executor.world_evolution_engine.scenario_runtime, ScenarioRuntime)
    assert restored.scenario_runtime.configuration == session.scenario_runtime.configuration
    assert restored.scenario_runtime.character_cards == session.scenario_runtime.character_cards


def test_proposals_are_immutable_candidates_only():
    from cognitive_sandbox.scenario.proposal import Proposal

    source = {"description": "possible development", "entities": ["entity-a"]}
    proposal = Proposal("proposal-1", "world_change", "provider", source, .7)
    source["entities"].append("entity-b")
    assert proposal.payload["entities"] == ("entity-a",)
    try:
        proposal.payload["description"] = "approved fact"
        assert False, "proposal payload must be immutable"
    except TypeError:
        pass


def test_lifecycle_memory_does_not_store_narrative_causes():
    memory = WorldMemory()
    private_text = "A world-specific chapter explains the secret."
    memory.record_opportunity("opp-1", "created", cause=private_text)
    memory.record_conflict("conflict-1", "changed", before={"status": "active", "private_field": private_text},
                           after={"status": "escalating", "private_field": private_text}, cause=private_text)
    memory.record_decision("entity-a", "inspect", reason_context=private_text)
    memory.record_world_tree("branch_expanded", "branch-1", cause=private_text)

    snapshot = repr(memory.snapshot())
    assert private_text not in snapshot
    assert "private_field" not in snapshot
    assert all(record.summary for record in (
        *memory.history.opportunity_history,
        *memory.history.conflict_history,
        *memory.history.decision_history,
        *memory.history.world_tree_history,
    ))
