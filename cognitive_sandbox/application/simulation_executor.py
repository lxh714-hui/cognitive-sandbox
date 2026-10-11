from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from cognitive_sandbox.application.simulation_runtime import SimulationRuntime
from cognitive_sandbox.domain.observations import PerceptionContext
from cognitive_sandbox.domain.simulation import SimulationMode, SimulationStepResult
from cognitive_sandbox.domain.world_events import WorldEvent


class ModeRuntime(Protocol):
    def process_event(
        self,
        world_event: WorldEvent,
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
    ) -> SimulationStepResult: ...


class SimulationExecutor:
    """Select a processing path for a mode without committing world actions."""

    _COGNITIVE_MODES = (
        SimulationMode.BASIC_COGNITION,
        SimulationMode.FULL_COGNITION,
        SimulationMode.DEEP_REASONING,
    )

    def __init__(
        self,
        simulation_runtime: SimulationRuntime,
        *,
        mode_runtimes: Mapping[SimulationMode, ModeRuntime] | None = None,
    ) -> None:
        self._mode_runtimes = {
            mode: simulation_runtime for mode in self._COGNITIVE_MODES
        }
        if mode_runtimes is not None:
            if not isinstance(mode_runtimes, Mapping):
                raise TypeError("mode_runtimes must map SimulationMode values to runtimes.")
            for mode, runtime in mode_runtimes.items():
                if not isinstance(mode, SimulationMode) or mode is SimulationMode.RULE_ONLY:
                    raise ValueError("Only cognitive SimulationMode paths can be overridden.")
                if not callable(getattr(runtime, "process_event", None)):
                    raise TypeError("Each mode runtime must provide process_event().")
                self._mode_runtimes[mode] = runtime

    def execute(
        self,
        mode: SimulationMode,
        world_event: WorldEvent,
        agent_ids: Sequence[str],
        perception_contexts: Mapping[str, PerceptionContext],
    ) -> SimulationStepResult:
        if not isinstance(mode, SimulationMode):
            raise TypeError("mode must be a SimulationMode.")
        if not isinstance(world_event, WorldEvent):
            raise TypeError("world_event must be a WorldEvent.")
        if mode is SimulationMode.RULE_ONLY:
            return SimulationStepResult(world_event.event_id, (), ())

        result = self._mode_runtimes[mode].process_event(
            world_event,
            agent_ids,
            perception_contexts,
        )
        if not isinstance(result, SimulationStepResult):
            raise TypeError("Mode runtime must return a SimulationStepResult.")
        if result.world_event_id != world_event.event_id:
            raise ValueError("Mode runtime returned a result for a different world event.")
        return result
