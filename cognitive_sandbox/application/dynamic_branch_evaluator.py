from __future__ import annotations

from collections.abc import Callable

from cognitive_sandbox.domain.story import (
    BranchScore,
    DynamicBranchScore,
    StoryBranch,
    StorySimulationResult,
)


class DynamicBranchEvaluator:
    """Simulate branches and expose constraint-based scores to search."""

    def __init__(self, simulate: Callable[[StoryBranch], StorySimulationResult]) -> None:
        if not callable(simulate):
            raise TypeError("simulate must be callable.")
        self._simulate = simulate
        self._scores: dict[str, DynamicBranchScore] = {}

    @property
    def dynamic_scores(self) -> tuple[DynamicBranchScore, ...]:
        return tuple(self._scores.values())

    def evaluate(self, branch: StoryBranch) -> DynamicBranchScore:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        result = self._simulate(branch)
        if not isinstance(result, StorySimulationResult):
            raise TypeError("simulate must return a StorySimulationResult.")
        if not result.events:
            raise ValueError("A branch simulation must contain attributable world events.")
        event_branch_ids = {event.branch_id for event in result.events}
        event_world_ids = {event.world_id for event in result.events}
        if event_branch_ids != {branch.branch_id} or event_world_ids != {branch.world_id}:
            raise ValueError("Simulation events must belong to the evaluated branch and world.")

        hard_passed = result.evaluation.accepted
        soft_score = result.evaluation.soft_score
        score = DynamicBranchScore(
            branch_id=branch.branch_id,
            simulation_id=result.simulation_id,
            hard_passed=hard_passed,
            soft_score=soft_score,
            final_score=soft_score if hard_passed else 0.0,
        )
        self._scores[branch.branch_id] = score
        return score

    def score(self, branch: StoryBranch) -> BranchScore:
        """Implement NarrativeSearch's scorer interface using real run results."""
        dynamic = self.evaluate(branch)
        reason = (
            f"simulation {dynamic.simulation_id} passed hard constraints"
            if dynamic.hard_passed
            else f"simulation {dynamic.simulation_id} failed hard constraints"
        )
        return BranchScore(branch.branch_id, dynamic.final_score, (reason,))
