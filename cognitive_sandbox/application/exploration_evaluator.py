from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from cognitive_sandbox.domain.story import (
    BranchExplorationResult,
    ExplorationEvaluation,
    StorySimulationResult,
)


class ExplorationEvaluator:
    """Summarize simulation quality for branches produced by exploration runs.

    A simulation is associated with a branch through the branch IDs on its
    world events. Results with no events cannot be attributed to a branch and
    are therefore excluded from branch scoring.
    """

    def __init__(self, *, evaluation_id_factory: Callable[[], str] | None = None) -> None:
        self._evaluation_id_factory = evaluation_id_factory or (lambda: str(uuid4()))

    def evaluate(
        self,
        exploration_results: Iterable[BranchExplorationResult],
        simulation_results: Iterable[StorySimulationResult],
    ) -> ExplorationEvaluation:
        if isinstance(exploration_results, (str, bytes)):
            raise TypeError("exploration_results must contain BranchExplorationResult values.")
        if isinstance(simulation_results, (str, bytes)):
            raise TypeError("simulation_results must contain StorySimulationResult values.")
        explorations = tuple(exploration_results)
        simulations = tuple(simulation_results)
        if any(not isinstance(item, BranchExplorationResult) for item in explorations):
            raise TypeError("exploration_results must contain only BranchExplorationResult values.")
        if any(not isinstance(item, StorySimulationResult) for item in simulations):
            raise TypeError("simulation_results must contain only StorySimulationResult values.")

        branches_by_id = {
            branch.branch_id: branch
            for exploration in explorations
            for branch in exploration.generated_branches
        }
        if sum(len(item.generated_branches) for item in explorations) != len(branches_by_id):
            raise ValueError("Exploration results must not repeat branch IDs.")

        # A simulation's events identify its route. Ignore results that cannot
        # be associated with exactly one explored branch.
        outcomes: dict[str, list[StorySimulationResult]] = {}
        for simulation in simulations:
            branch_ids = {event.branch_id for event in simulation.events}
            if len(branch_ids) != 1:
                continue
            branch_id = next(iter(branch_ids))
            if branch_id in branches_by_id:
                outcomes.setdefault(branch_id, []).append(simulation)

        successful = tuple(
            sorted(
                branch_id
                for branch_id, results in outcomes.items()
                if any(result.success for result in results)
            )
        )
        scored = [result for results in outcomes.values() for result in results]
        average = (
            sum(result.evaluation.soft_score for result in scored) / len(scored)
            if scored
            else 0.0
        )
        best_branch_id = None
        if outcomes:
            best_branch_id = min(
                outcomes,
                key=lambda branch_id: (
                    not any(result.success for result in outcomes[branch_id]),
                    not any(result.evaluation.accepted for result in outcomes[branch_id]),
                    -max(result.evaluation.soft_score for result in outcomes[branch_id]),
                    branch_id,
                ),
            )

        return ExplorationEvaluation(
            evaluation_id=self._evaluation_id_factory(),
            explored_count=len(branches_by_id),
            successful_branches=successful,
            best_branch_id=best_branch_id,
            average_soft_score=average,
        )
