from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.action_resolver import ActionResolver
from cognitive_sandbox.application.agent_runtime import AgentRuntime
from cognitive_sandbox.application.cognitive_runtime import CognitiveRuntime
from cognitive_sandbox.application.decision_runtime import DecisionRuntime
from cognitive_sandbox.application.event_loop import DiscreteEventLoop
from cognitive_sandbox.application.event_queue import SimulationEventQueue
from cognitive_sandbox.application.observation_layer import ObservationRuntime
from cognitive_sandbox.application.runtime_coordinator import RuntimeCoordinator
from cognitive_sandbox.application.simulation_runtime import SimulationRuntime
from cognitive_sandbox.application.story_simulation_runner import StorySimulationRunner
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.runtime_mode import StorySimulationConfig
from cognitive_sandbox.domain.story import HardConstraint, SoftConstraint, StorySimulationResult
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


class _AgentMap:
    def __init__(self, agents):
        self._agents = agents

    def get_agent(self, agent_id):
        return self._agents.get(agent_id)


def _agent(agent_id):
    return Agent(agent_id, "harbor", agent_id, "resident", "observant", agent_id)


def _context():
    return PerceptionContext("kitchen", "kitchen")


def _setup(tmp_path):
    store = SQLiteEventStore(tmp_path / "story-run.sqlite3")
    world = WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )
    initial_event = world.submit_action(
        ActionProposal(
            "break-cup",
            "liang-jing",
            "BREAK_OBJECT",
            "cup_001",
            {"location_id": "kitchen"},
            "main",
            "harbor",
            0,
        )
    )
    cognition = CognitiveRuntime(store)
    agent_runtime = AgentRuntime(
        _AgentMap({"lin-xia": _agent("lin-xia")}),
        ObservationRuntime(store),
        cognition,
        DecisionRuntime(cognition, store),
    )
    loop = DiscreteEventLoop(
        SimulationRuntime(RuntimeCoordinator(agent_runtime), ActionResolver()),
        world,
        SimulationEventQueue(),
    )
    runner = StorySimulationRunner(
        loop,
        store,
        simulation_id_factory=lambda: "story-run-1",
    )
    return store, world, initial_event, loop, runner


def test_story_runner_returns_steps_events_and_constraint_evaluation(tmp_path):
    store, world, initial_event, loop, runner = _setup(tmp_path)

    result = runner.run(
        StorySimulationConfig("harbor", "main", initial_world_revision=0),
        [initial_event],
        ["lin-xia"],
        {"lin-xia": _context()},
        hard_constraints=[
            HardConstraint(
                "no-death",
                "No character deaths.",
                forbidden_event_types=("CHARACTER_DIED",),
            )
        ],
        soft_constraints=[
            SoftConstraint(
                "prefer-inspection",
                "Prefer investigation scenes.",
                ("OBJECT_INSPECTED",),
            )
        ],
    )

    assert result.simulation_id == "story-run-1"
    assert result.success is True
    assert result.steps == 2
    assert [event.event_type for event in result.events] == [
        "BREAK_OBJECT",
        "OBJECT_INSPECTED",
    ]
    assert result.evaluation.accepted is True
    assert result.evaluation.source_event_ids == tuple(event.event_id for event in result.events)
    assert result.evaluation.soft_score == pytest.approx(0.5)
    assert loop.event_queue.size() == 0
    assert store.list_world_events("harbor") == list(result.events)
    assert world.world_revision == 2


def test_story_runner_reports_hard_constraint_failure_after_run(tmp_path):
    _, _, initial_event, _, runner = _setup(tmp_path)

    result = runner.run(
        StorySimulationConfig("harbor", "main"),
        [initial_event],
        [],
        {},
        hard_constraints=[
            HardConstraint(
                "no-breaking",
                "The cup must stay intact.",
                forbidden_event_types=("BREAK_OBJECT",),
            )
        ],
    )

    assert result.success is False
    assert result.evaluation.accepted is False
    assert result.evaluation.hard_violations == (f"{initial_event.event_id}:no-breaking",)


def test_story_simulation_result_is_immutable_and_validates_fields(tmp_path):
    _, _, initial_event, _, runner = _setup(tmp_path)
    result = runner.run(
        StorySimulationConfig("harbor", "main"),
        [initial_event],
        [],
        {},
    )

    with pytest.raises(FrozenInstanceError):
        result.success = False
    with pytest.raises(ValueError, match="steps"):
        StorySimulationResult(
            "run",
            True,
            -1,
            (initial_event,),
            result.evaluation,
        )


def test_story_runner_requires_committed_events_in_configured_scope(tmp_path):
    _, _, initial_event, _, runner = _setup(tmp_path)

    with pytest.raises(ValueError, match="configured world and branch"):
        runner.run(
            StorySimulationConfig("other-world", "main"),
            [initial_event],
            [],
            {},
        )

    with pytest.raises(ValueError, match="already be committed"):
        from cognitive_sandbox.domain.world_events import WorldEvent

        runner.run(
            StorySimulationConfig("harbor", "main"),
            [WorldEvent("uncommitted", "main", "harbor", "ANY", "actor", {}, 99)],
            [],
            {},
        )
