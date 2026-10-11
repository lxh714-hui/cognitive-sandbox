from __future__ import annotations

from collections.abc import Mapping, Sequence

from cognitive_sandbox.application.event_queue import SimulationEventQueue
from cognitive_sandbox.application.simulation_runtime import SimulationRuntime
from cognitive_sandbox.application.world_runtime import WorldRevisionConflict, WorldRuntime
from cognitive_sandbox.domain.actions import ResolvedAction
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.simulation import SimulationStepResult


class DiscreteEventLoop:
    """Process queued world events and enqueue events produced by accepted actions."""

    def __init__(
        self,
        simulation_runtime: SimulationRuntime,
        world_runtime: WorldRuntime,
        event_queue: SimulationEventQueue | None = None,
    ) -> None:
        self._simulation_runtime = simulation_runtime
        self._world_runtime = world_runtime
        self.event_queue = event_queue or SimulationEventQueue()

    def run(
        self,
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
        *,
        max_steps: int = 100,
    ) -> tuple[SimulationStepResult, ...]:
        """Drain up to max_steps events, preserving any remaining queue entries."""
        if isinstance(max_steps, bool) or not isinstance(max_steps, int):
            raise TypeError("max_steps must be an integer.")
        if max_steps < 1:
            raise ValueError("max_steps must be positive.")

        results: list[SimulationStepResult] = []
        while self.event_queue.size() and len(results) < max_steps:
            event = self.event_queue.pop()
            result = self._simulation_runtime.process_event(
                event,
                agent_ids,
                perception_contexts,
            )
            results.append(result)
            for resolved_action in result.resolved_actions:
                if not resolved_action.accepted:
                    continue
                try:
                    new_event = self._world_runtime.execute_action(resolved_action)
                except WorldRevisionConflict:
                    # Another accepted proposal from this same step may already have advanced
                    # the world revision. Never rewrite its proposal's source revision.
                    continue
                if new_event is not None:
                    self.event_queue.push(new_event)
        return tuple(results)
