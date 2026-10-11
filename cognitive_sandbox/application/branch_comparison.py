from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from cognitive_sandbox.domain.story import BranchComparisonResult, StorySimulationResult


class BranchComparisonService:
    """Compare simulation outcomes using deterministic success and constraint ordering."""

    def __init__(self, *, comparison_id_factory: Callable[[], str] | None = None) -> None:
        self._comparison_id_factory = comparison_id_factory or (lambda: str(uuid4()))

    def compare(self, results: Iterable[StorySimulationResult]) -> BranchComparisonResult:
        if isinstance(results, (str, bytes)):
            raise TypeError("results must be an iterable of StorySimulationResult values.")
        simulations = tuple(results)
        if not simulations:
            raise ValueError("At least one simulation result is required.")
        if any(not isinstance(result, StorySimulationResult) for result in simulations):
            raise TypeError("results must contain only StorySimulationResult values.")

        simulation_ids = tuple(result.simulation_id for result in simulations)
        if len(set(simulation_ids)) != len(simulation_ids):
            raise ValueError("Simulation IDs must be unique within a comparison.")
        ranked = sorted(
            simulations,
            key=lambda result: (
                not result.success,
                not result.evaluation.accepted,
                -result.evaluation.soft_score,
                result.simulation_id,
            ),
        )
        ranking = tuple(result.simulation_id for result in ranked)
        successful = tuple(result.simulation_id for result in ranked if result.success)
        return BranchComparisonResult(
            comparison_id=self._comparison_id_factory(),
            simulation_ids=simulation_ids,
            successful_simulations=successful,
            ranking=ranking,
        )
