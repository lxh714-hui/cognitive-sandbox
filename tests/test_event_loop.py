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
from cognitive_sandbox.application.world_runtime import WorldRuntime
from cognitive_sandbox.domain.actions import ActionProposal
from cognitive_sandbox.domain.models import Agent
from cognitive_sandbox.domain.observations import PerceptionContext
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


def _world(store):
    return WorldRuntime(
        store,
        world_id="harbor",
        branch_id="main",
        breakable_object_ids={"cup_001"},
    )


def _loop(store, world, agent_ids, queue=None):
    cognition = CognitiveRuntime(store)
    agent_runtime = AgentRuntime(
        _AgentMap({agent_id: _agent(agent_id) for agent_id in agent_ids}),
        ObservationRuntime(store),
        cognition,
        DecisionRuntime(cognition, store),
    )
    simulation = SimulationRuntime(RuntimeCoordinator(agent_runtime), ActionResolver())
    return DiscreteEventLoop(simulation, world, queue)


def _initial_break(world):
    return world.submit_action(
        ActionProposal(
            proposal_id="break-cup",
            actor_id="liang-jing",
            action_type="BREAK_OBJECT",
            target_id="cup_001",
            payload={"location_id": "kitchen"},
            branch_id="main",
            world_id="harbor",
            base_world_revision=0,
        )
    )


def test_simulation_event_queue_is_fifo_and_peek_does_not_remove(tmp_path):
    store = SQLiteEventStore(tmp_path / "queue.sqlite3")
    world = _world(store)
    event = _initial_break(world)
    queue = SimulationEventQueue()

    queue.push(event)

    assert queue.size() == 1
    assert queue.peek() == event
    assert queue.size() == 1
    assert queue.pop() == event
    assert queue.size() == 0
    with pytest.raises(IndexError):
        queue.pop()
    with pytest.raises(IndexError):
        queue.peek()


def test_discrete_event_loop_executes_accepted_action_and_queues_new_event(tmp_path):
    store = SQLiteEventStore(tmp_path / "event-loop.sqlite3")
    world = _world(store)
    initial_event = _initial_break(world)
    queue = SimulationEventQueue()
    queue.push(initial_event)
    loop = _loop(store, world, ["lin-xia"], queue)

    steps = loop.run(["lin-xia"], {"lin-xia": _context()})

    assert len(steps) == 2
    assert steps[0].world_event_id == initial_event.event_id
    assert steps[0].resolved_actions[0].accepted is True
    assert steps[1].world_event_id != initial_event.event_id
    assert steps[1].resolved_actions == ()
    events = store.list_world_events("harbor")
    assert [event.event_type for event in events] == ["BREAK_OBJECT", "OBJECT_INSPECTED"]
    assert [event.world_revision for event in events] == [1, 2]
    assert loop.event_queue.size() == 0
    assert world.world_revision == 2


def test_discrete_event_loop_skips_rejected_actions(tmp_path):
    store = SQLiteEventStore(tmp_path / "rejected-loop.sqlite3")
    world = _world(store)
    event = _initial_break(world)
    queue = SimulationEventQueue()
    queue.push(event)

    class NoProposalSimulation:
        def process_event(self, world_event, agent_ids, perception_contexts):
            from cognitive_sandbox.domain.actions import ResolvedAction
            from cognitive_sandbox.domain.simulation import SimulationStepResult

            rejected = ResolvedAction(
                ActionProposal(
                    proposal_id="rejected",
                    actor_id="lin-xia",
                    action_type="INSPECT_OBJECT",
                    target_id="cup_001",
                    payload={},
                    branch_id="main",
                    world_id="harbor",
                    base_world_revision=1,
                ),
                False,
                "Rejected by resolver.",
            )
            return SimulationStepResult(world_event.event_id, (rejected.action,), (rejected,))

    loop = DiscreteEventLoop(NoProposalSimulation(), world, queue)

    steps = loop.run([], {})

    assert len(steps) == 1
    assert store.list_world_events("harbor") == [event]
    assert world.world_revision == 1
    assert loop.event_queue.size() == 0


def test_discrete_event_loop_respects_step_limit_and_keeps_pending_events(tmp_path):
    store = SQLiteEventStore(tmp_path / "step-limit.sqlite3")
    world = _world(store)
    event = _initial_break(world)
    queue = SimulationEventQueue()
    queue.push(event)

    class NoActionSimulation:
        def process_event(self, world_event, agent_ids, perception_contexts):
            from cognitive_sandbox.domain.simulation import SimulationStepResult

            return SimulationStepResult(world_event.event_id, (), ())

    loop = DiscreteEventLoop(NoActionSimulation(), world, queue)
    queue.push(event)

    results = loop.run([], {}, max_steps=1)

    assert len(results) == 1
    assert loop.event_queue.size() == 1
    with pytest.raises(ValueError, match="positive"):
        loop.run([], {}, max_steps=0)
