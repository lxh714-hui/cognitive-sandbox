from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol
from uuid import uuid4

from cognitive_sandbox.application.event_loop import DiscreteEventLoop
from cognitive_sandbox.application.story_constraints import StoryConstraintEvaluator
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.runtime_mode import StorySimulationConfig
from cognitive_sandbox.domain.story import (
    ConstraintEvaluation,
    HardConstraint,
    SoftConstraint,
    StorySimulationResult,
)
from cognitive_sandbox.domain.world_events import WorldEvent


class StoryEventReader(Protocol):
    def list_world_events(self, world_id: str) -> list[WorldEvent]: ...


class StorySimulationRunner:
    """Run a bounded story event loop and evaluate its resulting event stream."""

    def __init__(
        self,
        event_loop: DiscreteEventLoop,
        event_reader: StoryEventReader,
        constraint_evaluator: StoryConstraintEvaluator | None = None,
        *,
        simulation_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._event_loop = event_loop
        self._event_reader = event_reader
        self._constraint_evaluator = constraint_evaluator or StoryConstraintEvaluator()
        self._simulation_id_factory = simulation_id_factory or (lambda: str(uuid4()))

    def run(
        self,
        config: StorySimulationConfig,
        initial_events: Iterable[WorldEvent],
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
        *,
        hard_constraints: Iterable[HardConstraint] = (),
        soft_constraints: Iterable[SoftConstraint] = (),
        max_steps: int = 100,
        simulation_id: str | None = None,
    ) -> StorySimulationResult:
        if not isinstance(config, StorySimulationConfig):
            raise TypeError("config must be a StorySimulationConfig.")
        if simulation_id is not None and (not isinstance(simulation_id, str) or not simulation_id.strip()):
            raise ValueError("simulation_id must be None or a non-empty string.")
        initial = tuple(initial_events)
        if not initial:
            raise ValueError("initial_events must contain at least one committed event.")
        if any(not isinstance(event, WorldEvent) for event in initial):
            raise TypeError("initial_events must contain only WorldEvent values.")
        if any(
            event.world_id != config.world_id or event.branch_id != config.branch_id
            for event in initial
        ):
            raise ValueError("Initial events must belong to the configured world and branch.")

        persisted_before = tuple(self._event_reader.list_world_events(config.world_id))
        persisted_by_id = {event.event_id: event for event in persisted_before}
        if any(persisted_by_id.get(event.event_id) != event for event in initial):
            raise ValueError("Every initial event must already be committed to the world store.")

        for event in initial:
            self._event_loop.event_queue.push(event)
        steps = self._event_loop.run(
            agent_ids,
            perception_contexts,
            max_steps=max_steps,
        )

        persisted_after = self._event_reader.list_world_events(config.world_id)
        created_events = [
            event
            for event in persisted_after
            if event.event_id not in persisted_by_id
            and event.branch_id == config.branch_id
        ]
        events_by_id = {event.event_id: event for event in (*initial, *created_events)}
        story_events = tuple(
            sorted(events_by_id.values(), key=lambda event: (event.world_revision, event.event_id))
        )
        evaluation: ConstraintEvaluation = self._constraint_evaluator.evaluate_events(
            story_events,
            hard_constraints=hard_constraints,
            soft_constraints=soft_constraints,
        )
        return StorySimulationResult(
            simulation_id=simulation_id or self._simulation_id_factory(),
            success=evaluation.accepted and self._event_loop.event_queue.size() == 0,
            steps=len(steps),
            events=story_events,
            evaluation=evaluation,
        )
