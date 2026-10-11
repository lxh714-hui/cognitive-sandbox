from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from collections.abc import Iterable
from typing import ClassVar

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.world_events import WorldEvent


def _string_tuple(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TypeError(f"{field_name} must be a collection of strings.")
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value.strip() for value in normalized):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return normalized


@dataclass(frozen=True)
class StoryObjective:
    objective_id: str
    description: str
    priority: int

    def __post_init__(self) -> None:
        for name in ("objective_id", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("priority must be an integer.")
        if self.priority < 0:
            raise ValueError("priority must be non-negative.")


@dataclass(frozen=True)
class StoryBranch:
    """One immutable route in a story simulation's branch tree."""

    branch_id: str
    parent_branch_id: str | None
    world_id: str
    revision: int
    divergence_event_id: str | None
    divergence_action: ActionCandidate | None = None

    def __post_init__(self) -> None:
        for name in ("branch_id", "world_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        for name in ("parent_branch_id", "divergence_event_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be None or a non-empty string.")
        if self.parent_branch_id == self.branch_id:
            raise ValueError("A story branch cannot be its own parent.")
        if self.divergence_action is not None and not isinstance(
            self.divergence_action, ActionCandidate
        ):
            raise TypeError("divergence_action must be an ActionCandidate or None.")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError("revision must be an integer.")
        if self.revision < 0:
            raise ValueError("revision must be non-negative.")


@dataclass(frozen=True)
class BranchSimulationRecord:
    simulation_id: str
    branch_id: str
    result_status: str

    STATUSES: ClassVar[frozenset[str]] = frozenset({"pending", "succeeded", "failed"})

    def __post_init__(self) -> None:
        for name in ("simulation_id", "branch_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.result_status, str) or self.result_status not in self.STATUSES:
            raise ValueError("result_status must be pending, succeeded, or failed.")


@dataclass(frozen=True)
class BranchGenerationResult:
    generation_id: str
    source_branch_id: str
    created_branches: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("generation_id", "source_branch_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        branches = _string_tuple(self.created_branches, "created_branches")
        if len(set(branches)) != len(branches):
            raise ValueError("created_branches must contain unique branch IDs.")
        if self.source_branch_id in branches:
            raise ValueError("created_branches must not include the source branch.")
        object.__setattr__(self, "created_branches", branches)


@dataclass(frozen=True)
class BranchExplorationConfig:
    max_depth: int
    max_branches_per_node: int

    def __post_init__(self) -> None:
        for name in ("max_depth", "max_branches_per_node"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer.")
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative.")
        if self.max_branches_per_node < 1:
            raise ValueError("max_branches_per_node must be positive.")


@dataclass(frozen=True)
class BranchExplorationResult:
    exploration_id: str
    root_branch_id: str
    generated_branches: tuple[StoryBranch, ...]
    branch_depths: tuple[int, ...]
    expanded_branch_ids: tuple[str, ...]
    depth_reached: int

    def __post_init__(self) -> None:
        for name in ("exploration_id", "root_branch_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        branches = tuple(self.generated_branches)
        if any(not isinstance(branch, StoryBranch) for branch in branches):
            raise TypeError("generated_branches must contain StoryBranch values.")
        depths = tuple(self.branch_depths)
        if len(depths) != len(branches):
            raise ValueError("branch_depths must align with generated_branches.")
        if any(isinstance(depth, bool) or not isinstance(depth, int) or depth < 1 for depth in depths):
            raise ValueError("Generated branch depths must be positive integers.")
        expanded = _string_tuple(self.expanded_branch_ids, "expanded_branch_ids")
        if len(set(expanded)) != len(expanded):
            raise ValueError("expanded_branch_ids must be unique.")
        branch_ids = tuple(branch.branch_id for branch in branches)
        if len(set(branch_ids)) != len(branch_ids) or self.root_branch_id in branch_ids:
            raise ValueError("generated branch IDs must be unique and exclude the root.")
        if isinstance(self.depth_reached, bool) or not isinstance(self.depth_reached, int):
            raise TypeError("depth_reached must be a non-negative integer.")
        if self.depth_reached < 0 or (depths and self.depth_reached != max(depths)):
            raise ValueError("depth_reached must match the deepest generated branch.")
        if not depths and self.depth_reached != 0:
            raise ValueError("depth_reached must be zero when no branches were generated.")
        object.__setattr__(self, "generated_branches", branches)
        object.__setattr__(self, "branch_depths", depths)
        object.__setattr__(self, "expanded_branch_ids", expanded)


@dataclass(frozen=True)
class ExplorationEvaluation:
    """Aggregate outcome and soft-constraint quality for explored branches."""

    evaluation_id: str
    explored_count: int
    successful_branches: tuple[str, ...]
    best_branch_id: str | None
    average_soft_score: float

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, str) or not self.evaluation_id.strip():
            raise ValueError("evaluation_id must not be empty.")
        if isinstance(self.explored_count, bool) or not isinstance(self.explored_count, int):
            raise TypeError("explored_count must be a non-negative integer.")
        if self.explored_count < 0:
            raise ValueError("explored_count must be non-negative.")
        successful = _string_tuple(self.successful_branches, "successful_branches")
        if len(set(successful)) != len(successful):
            raise ValueError("successful_branches must contain unique branch IDs.")
        if len(successful) > self.explored_count:
            raise ValueError("successful_branches cannot exceed explored_count.")
        if self.best_branch_id is not None and (
            not isinstance(self.best_branch_id, str) or not self.best_branch_id.strip()
        ):
            raise ValueError("best_branch_id must be None or a non-empty string.")
        if isinstance(self.average_soft_score, bool) or not isinstance(
            self.average_soft_score, (int, float)
        ):
            raise TypeError("average_soft_score must be a number between 0 and 1.")
        if not math.isfinite(self.average_soft_score) or not 0 <= self.average_soft_score <= 1:
            raise ValueError("average_soft_score must be between 0 and 1.")
        if self.explored_count == 0 and (successful or self.best_branch_id is not None):
            raise ValueError("An empty exploration cannot have successful or best branches.")
        object.__setattr__(self, "successful_branches", successful)
        object.__setattr__(self, "average_soft_score", float(self.average_soft_score))


class SearchStrategy(str, Enum):
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    SCORE_GUIDED = "score_guided"


@dataclass(frozen=True)
class SearchPolicy:
    strategy: SearchStrategy
    max_depth: int
    max_nodes: int
    max_branches_per_node: int

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, SearchStrategy):
            raise TypeError("strategy must be a SearchStrategy.")
        for name in ("max_depth", "max_nodes", "max_branches_per_node"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer.")
        if self.max_depth < 0:
            raise ValueError("max_depth must be non-negative.")
        if self.max_nodes < 1:
            raise ValueError("max_nodes must include at least the root node.")
        if self.max_branches_per_node < 1:
            raise ValueError("max_branches_per_node must be positive.")


@dataclass(frozen=True)
class BranchScore:
    branch_id: str
    score: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be a number between 0 and 1.")
        if not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        reasons = _string_tuple(self.reasons, "reasons")
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "reasons", reasons)


@dataclass(frozen=True)
class DynamicBranchScore:
    branch_id: str
    simulation_id: str
    hard_passed: bool
    soft_score: float
    final_score: float

    def __post_init__(self) -> None:
        for name in ("branch_id", "simulation_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.hard_passed, bool):
            raise TypeError("hard_passed must be a boolean.")
        for name in ("soft_score", "final_score"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number between 0 and 1.")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
        expected = float(self.soft_score) if self.hard_passed else 0.0
        if float(self.final_score) != expected:
            raise ValueError("final_score must be soft_score after hard pass, otherwise zero.")
        object.__setattr__(self, "soft_score", float(self.soft_score))
        object.__setattr__(self, "final_score", float(self.final_score))


@dataclass(frozen=True)
class NarrativeSearchResult:
    search_id: str
    root_branch_id: str
    strategy: SearchStrategy
    generated_branches: tuple[StoryBranch, ...]
    expanded_branch_ids: tuple[str, ...]
    branch_scores: tuple[BranchScore, ...]
    best_branch_id: str | None
    depth_reached: int

    def __post_init__(self) -> None:
        for name in ("search_id", "root_branch_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.strategy, SearchStrategy):
            raise TypeError("strategy must be a SearchStrategy.")
        branches = tuple(self.generated_branches)
        if any(not isinstance(branch, StoryBranch) for branch in branches):
            raise TypeError("generated_branches must contain StoryBranch values.")
        branch_ids = tuple(branch.branch_id for branch in branches)
        if len(set(branch_ids)) != len(branch_ids) or self.root_branch_id in branch_ids:
            raise ValueError("generated branch IDs must be unique and exclude the root.")
        expanded = _string_tuple(self.expanded_branch_ids, "expanded_branch_ids")
        if len(set(expanded)) != len(expanded):
            raise ValueError("expanded_branch_ids must be unique.")
        scores = tuple(self.branch_scores)
        if any(not isinstance(score, BranchScore) for score in scores):
            raise TypeError("branch_scores must contain BranchScore values.")
        if {score.branch_id for score in scores} != set(branch_ids) or len(scores) != len(branches):
            raise ValueError("branch_scores must contain one score for every generated branch.")
        if self.best_branch_id is not None and self.best_branch_id not in branch_ids:
            raise ValueError("best_branch_id must identify a generated branch.")
        if isinstance(self.depth_reached, bool) or not isinstance(self.depth_reached, int):
            raise TypeError("depth_reached must be a non-negative integer.")
        if self.depth_reached < 0:
            raise ValueError("depth_reached must be non-negative.")
        object.__setattr__(self, "generated_branches", branches)
        object.__setattr__(self, "expanded_branch_ids", expanded)
        object.__setattr__(self, "branch_scores", scores)


@dataclass(frozen=True)
class HardConstraint:
    """Event-type rule that can invalidate a story event."""

    constraint_id: str
    description: str
    forbidden_event_types: tuple[str, ...] = ()
    allowed_event_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("constraint_id", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        forbidden = _string_tuple(self.forbidden_event_types, "forbidden_event_types")
        allowed = _string_tuple(self.allowed_event_types, "allowed_event_types")
        if not forbidden and not allowed:
            raise ValueError("A hard constraint must define allowed or forbidden event types.")
        if set(forbidden) & set(allowed):
            raise ValueError("An event type cannot be both allowed and forbidden.")
        object.__setattr__(self, "forbidden_event_types", forbidden)
        object.__setattr__(self, "allowed_event_types", allowed)


@dataclass(frozen=True)
class SoftConstraint:
    """Weighted event-type preference used to score story consistency."""

    constraint_id: str
    description: str
    preferred_event_types: tuple[str, ...]
    weight: float = 1.0

    def __post_init__(self) -> None:
        for name in ("constraint_id", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        preferred = _string_tuple(self.preferred_event_types, "preferred_event_types")
        if not preferred:
            raise ValueError("preferred_event_types must not be empty.")
        if isinstance(self.weight, bool) or not isinstance(self.weight, (int, float)):
            raise TypeError("weight must be a number between 0 and 1.")
        if not math.isfinite(self.weight) or not 0 <= self.weight <= 1:
            raise ValueError("weight must be between 0 and 1.")
        object.__setattr__(self, "preferred_event_types", preferred)
        object.__setattr__(self, "weight", float(self.weight))


@dataclass(frozen=True)
class ConstraintEvaluation:
    world_event_id: str
    accepted: bool
    hard_violations: tuple[str, ...]
    soft_score: float
    matched_soft_constraints: tuple[str, ...]
    source_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.world_event_id, str) or not self.world_event_id.strip():
            raise ValueError("world_event_id must not be empty.")
        if not isinstance(self.accepted, bool):
            raise TypeError("accepted must be a boolean.")
        violations = _string_tuple(self.hard_violations, "hard_violations")
        matches = _string_tuple(self.matched_soft_constraints, "matched_soft_constraints")
        source_event_ids = self.source_event_ids or (self.world_event_id,)
        source_event_ids = _string_tuple(source_event_ids, "source_event_ids")
        if isinstance(self.soft_score, bool) or not isinstance(self.soft_score, (int, float)):
            raise TypeError("soft_score must be a number between 0 and 1.")
        if not math.isfinite(self.soft_score) or not 0 <= self.soft_score <= 1:
            raise ValueError("soft_score must be between 0 and 1.")
        if self.accepted != (not violations):
            raise ValueError("accepted must be false exactly when hard violations exist.")
        object.__setattr__(self, "hard_violations", violations)
        object.__setattr__(self, "matched_soft_constraints", matches)
        object.__setattr__(self, "soft_score", float(self.soft_score))
        object.__setattr__(self, "source_event_ids", source_event_ids)


@dataclass(frozen=True)
class StorySimulationResult:
    simulation_id: str
    success: bool
    steps: int
    events: tuple[WorldEvent, ...]
    evaluation: ConstraintEvaluation

    def __post_init__(self) -> None:
        if not isinstance(self.simulation_id, str) or not self.simulation_id.strip():
            raise ValueError("simulation_id must not be empty.")
        if not isinstance(self.success, bool):
            raise TypeError("success must be a boolean.")
        if isinstance(self.steps, bool) or not isinstance(self.steps, int):
            raise TypeError("steps must be a non-negative integer.")
        if self.steps < 0:
            raise ValueError("steps must be non-negative.")
        if isinstance(self.events, (str, bytes)):
            raise TypeError("events must be a collection of WorldEvent values.")
        events = tuple(self.events)
        if any(not isinstance(event, WorldEvent) for event in events):
            raise TypeError("events must contain only WorldEvent values.")
        if not isinstance(self.evaluation, ConstraintEvaluation):
            raise TypeError("evaluation must be a ConstraintEvaluation.")
        object.__setattr__(self, "events", events)


@dataclass(frozen=True)
class BranchComparisonResult:
    comparison_id: str
    simulation_ids: tuple[str, ...]
    successful_simulations: tuple[str, ...]
    ranking: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.comparison_id, str) or not self.comparison_id.strip():
            raise ValueError("comparison_id must not be empty.")
        simulation_ids = _string_tuple(self.simulation_ids, "simulation_ids")
        successful = _string_tuple(self.successful_simulations, "successful_simulations")
        ranking = _string_tuple(self.ranking, "ranking")
        if not simulation_ids:
            raise ValueError("simulation_ids must not be empty.")
        if len(set(simulation_ids)) != len(simulation_ids):
            raise ValueError("simulation_ids must be unique.")
        if len(set(successful)) != len(successful) or not set(successful).issubset(simulation_ids):
            raise ValueError("successful_simulations must be unique IDs from simulation_ids.")
        if len(ranking) != len(simulation_ids) or set(ranking) != set(simulation_ids):
            raise ValueError("ranking must contain each simulation ID exactly once.")
