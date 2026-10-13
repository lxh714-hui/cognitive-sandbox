from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.scenario_loader import ScenarioLoader
from cognitive_sandbox.character_presence.entry_rule import EntryRule
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.world_evolution import WorldEvolutionEngine


FIXTURE = Path(__file__).parent / "fixtures" / "blank_scenario"


def test_blank_package_loads_world_runs_tick_generates_npc_action_and_processes_event():
    loader = ScenarioLoader(package_root=FIXTURE.parent)
    scenario = loader.load("blank_world")
    assert scenario is not None
    assert scenario.name == "空白世界"

    session = GameLauncher(scenario_loader=loader).start_scenario("blank_world")
    assert session.world_state["initialized"] is True
    assert tuple(context.character_id for context in session.agent_contexts) == ("player_1", "person_2")

    session.presence_manager.add_rule(EntryRule("person_2", trigger_event_types=("world_tick",)))
    session.presence_manager.evaluate_entry("person_2", event_type="world_tick")
    session.presence_manager.introduce("person_2", current_location=None)
    session.presence_manager.activate("person_2")
    executor = session.executor
    now = executor.world_clock.current_time()
    context = SimpleNamespace(
        world_clock=executor.world_clock,
        world_state=session.world_state,
        agent_contexts=session.agent_contexts,
        event_timeline=executor.event_timeline,
        relationship_manager=executor.relationship_manager,
        emotion_engine=executor.emotion_engine,
        cognitive_engine=executor.cognitive_engine,
        knowledge_retriever=executor.knowledge_retriever,
        motivation_manager=executor.motivation_manager,
        narrative_pressure=None,
    )
    tick_result = executor._simulation_tick.run(session.agent_context, session.world_state, "quiet")
    assert tick_result.events
    executor.event_pipeline.publish(tick_result.events[0], context=context)
    assert any(record.event_id == tick_result.events[0].event_id
               for record in executor.event_timeline.events)

    tick = WorldEvent("blank-tick", "main", executor.world_id, "world_tick", "system", {}, 1,
                      timestamp=now.isoformat())
    published = executor.event_pipeline.publish(tick, context=context)

    npc_events = tuple(event for event in published if event.actor_id == "person_2")
    assert npc_events
    assert npc_events[0].event_type == "npc_observed"
    assert any(record.event_id == npc_events[0].event_id for record in executor.event_timeline.events)
    assert isinstance(executor.world_evolution_engine, WorldEvolutionEngine)


def test_world_specific_terms_cannot_reenter_engine_layers():
    root = Path(__file__).parents[1] / "cognitive_sandbox"
    forbidden = ("clinic", "doctor", "灰港", "repair_clinic", "medical_station", "example_world")
    layers = ("application", "domain", "world_evolution", "npc", "goal")
    offenders = []
    for layer in layers:
        for path in (root / layer).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for term in forbidden:
                if term.casefold() in source.casefold():
                    offenders.append(f"{path.relative_to(root)}: {term}")
    assert offenders == []
