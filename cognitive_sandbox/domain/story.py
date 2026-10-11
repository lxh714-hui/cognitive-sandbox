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
class ExpansionPolicy:
    max_branches_per_expansion: int
    max_total_expansions: int

    def __post_init__(self) -> None:
        for name in ("max_branches_per_expansion", "max_total_expansions"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-negative integer.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")


@dataclass(frozen=True)
class RolloutPolicy:
    """Inclusive lower and upper limits for a branch's simulation batch."""

    min_rollouts: int
    max_rollouts: int

    def __post_init__(self) -> None:
        for name in ("min_rollouts", "max_rollouts"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-negative integer.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")
        if self.min_rollouts > self.max_rollouts:
            raise ValueError("min_rollouts must not exceed max_rollouts.")


@dataclass(frozen=True)
class RolloutAllocation:
    branch_id: str
    rollout_count: int
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        if isinstance(self.rollout_count, bool) or not isinstance(self.rollout_count, int):
            raise TypeError("rollout_count must be a non-negative integer.")
        if self.rollout_count < 0:
            raise ValueError("rollout_count must be non-negative.")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty.")


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
class BranchValue:
    branch_id: str
    value: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("value must be a number between 0 and 1.")
        if not math.isfinite(self.value) or not 0 <= self.value <= 1:
            raise ValueError("value must be between 0 and 1.")
        reasons = _string_tuple(self.reasons, "reasons")
        object.__setattr__(self, "value", float(self.value))
        object.__setattr__(self, "reasons", reasons)


@dataclass(frozen=True)
class BranchEvaluationSummary:
    branch_id: str
    sample_count: int
    success_count: int
    success_rate: float
    average_soft_score: float
    confidence: float

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        for name in ("sample_count", "success_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-negative integer.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")
        if self.success_count > self.sample_count:
            raise ValueError("success_count must not exceed sample_count.")
        for name in ("success_rate", "average_soft_score", "confidence"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number between 0 and 1.")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
        if self.sample_count == 0 and (self.success_rate != 0 or self.average_soft_score != 0):
            raise ValueError("An empty summary must have zero rates and scores.")
        object.__setattr__(self, "success_rate", float(self.success_rate))
        object.__setattr__(self, "average_soft_score", float(self.average_soft_score))
        object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True)
class ConstraintCheck:
    constraint_id: str
    passed: bool
    reason: str

    def __post_init__(self) -> None:
        for name in ("constraint_id", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.passed, bool):
            raise TypeError("passed must be a boolean.")


@dataclass(frozen=True)
class RoleStateCheck:
    role_id: str
    valid: bool
    reason: str

    def __post_init__(self) -> None:
        for name in ("role_id", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.valid, bool):
            raise TypeError("valid must be a boolean.")


@dataclass(frozen=True)
class PruningPolicy:
    minimum_value: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.minimum_value, bool) or not isinstance(
            self.minimum_value, (int, float)
        ):
            raise TypeError("minimum_value must be a number between 0 and 1.")
        if not math.isfinite(self.minimum_value) or not 0 <= self.minimum_value <= 1:
            raise ValueError("minimum_value must be between 0 and 1.")
        object.__setattr__(self, "minimum_value", float(self.minimum_value))


@dataclass(frozen=True)
class PruningDecision:
    branch_id: str
    kept: bool
    reason: str

    def __post_init__(self) -> None:
        for name in ("branch_id", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.kept, bool):
            raise TypeError("kept must be a boolean.")


@dataclass(frozen=True)
class ExplorationPlan:
    branch_id: str
    should_explore: bool
    priority: float
    expansion_policy: ExpansionPolicy
    rollout_allocation: RolloutAllocation
    pruning_decision: PruningDecision

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        if not isinstance(self.should_explore, bool):
            raise TypeError("should_explore must be a boolean.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, (int, float)):
            raise TypeError("priority must be a number between 0 and 1.2.")
        if not math.isfinite(self.priority) or not 0 <= self.priority <= 1.2:
            raise ValueError("priority must be between 0 and 1.2.")
        if not isinstance(self.expansion_policy, ExpansionPolicy):
            raise TypeError("expansion_policy must be an ExpansionPolicy.")
        if not isinstance(self.rollout_allocation, RolloutAllocation):
            raise TypeError("rollout_allocation must be a RolloutAllocation.")
        if not isinstance(self.pruning_decision, PruningDecision):
            raise TypeError("pruning_decision must be a PruningDecision.")
        if self.rollout_allocation.branch_id != self.branch_id:
            raise ValueError("rollout_allocation must belong to the planned branch.")
        if self.pruning_decision.branch_id != self.branch_id:
            raise ValueError("pruning_decision must belong to the planned branch.")
        if self.should_explore != self.pruning_decision.kept:
            raise ValueError("should_explore must match the pruning decision.")
        object.__setattr__(self, "priority", float(self.priority))


@dataclass(frozen=True)
class ExplorationExecutionResult:
    branch_id: str
    executed: bool
    expanded_count: int
    rollout_count: int
    feedback_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.branch_id, str) or not self.branch_id.strip():
            raise ValueError("branch_id must not be empty.")
        if not isinstance(self.executed, bool):
            raise TypeError("executed must be a boolean.")
        for name in ("expanded_count", "rollout_count", "feedback_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-negative integer.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")
        if not self.executed and any(
            getattr(self, name) != 0
            for name in ("expanded_count", "rollout_count", "feedback_count")
        ):
            raise ValueError("A non-executed result must have zero counts.")


@dataclass(frozen=True)
class ExplorationLoopPolicy:
    max_iterations: int
    stop_on_no_feedback: bool

    def __post_init__(self) -> None:
        if isinstance(self.max_iterations, bool) or not isinstance(self.max_iterations, int):
            raise TypeError("max_iterations must be a non-negative integer.")
        if self.max_iterations < 0:
            raise ValueError("max_iterations must be non-negative.")
        if not isinstance(self.stop_on_no_feedback, bool):
            raise TypeError("stop_on_no_feedback must be a boolean.")


@dataclass(frozen=True)
class ExplorationLoopResult:
    iterations: int
    executed_count: int
    total_feedback_count: int
    stopped_reason: str

    def __post_init__(self) -> None:
        for name in ("iterations", "executed_count", "total_feedback_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a non-negative integer.")
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")
        if self.executed_count > self.iterations:
            raise ValueError("executed_count must not exceed iterations.")
        if not isinstance(self.stopped_reason, str) or not self.stopped_reason.strip():
            raise ValueError("stopped_reason must not be empty.")


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
    branch_values: tuple[BranchValue, ...] = ()

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
        values = tuple(self.branch_values)
        if any(not isinstance(value, BranchValue) for value in values):
            raise TypeError("branch_values must contain BranchValue values.")
        if values and (
            {value.branch_id for value in values} != set(branch_ids)
            or len(values) != len(branches)
        ):
            raise ValueError("branch_values must contain one value for every generated branch.")
        if self.best_branch_id is not None and self.best_branch_id not in branch_ids:
            raise ValueError("best_branch_id must identify a generated branch.")
        if isinstance(self.depth_reached, bool) or not isinstance(self.depth_reached, int):
            raise TypeError("depth_reached must be a non-negative integer.")
        if self.depth_reached < 0:
            raise ValueError("depth_reached must be non-negative.")
        object.__setattr__(self, "generated_branches", branches)
        object.__setattr__(self, "expanded_branch_ids", expanded)
        object.__setattr__(self, "branch_scores", scores)
        object.__setattr__(self, "branch_values", values)


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
