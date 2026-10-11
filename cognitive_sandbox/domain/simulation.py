from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import ClassVar

from cognitive_sandbox.domain.actions import ActionProposal, ResolvedAction


class SimulationMode(str, Enum):
    RULE_ONLY = "rule_only"
    BASIC_COGNITION = "basic_cognition"
    FULL_COGNITION = "full_cognition"
    DEEP_REASONING = "deep_reasoning"


@dataclass(frozen=True)
class EventImportance:
    """Deterministic importance score and corresponding simulation detail level."""

    score: float
    level: str

    LEVELS: ClassVar[frozenset[str]] = frozenset({"low", "medium", "high"})

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("score must be a number between 0 and 1.")
        if not math.isfinite(self.score) or not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1.")
        object.__setattr__(self, "score", float(self.score))
        if not isinstance(self.level, str) or self.level not in self.LEVELS:
            raise ValueError("level must be low, medium, or high.")


@dataclass(frozen=True)
class SimulationStepResult:
    """Immutable output from coordinating and resolving one committed world event."""

    world_event_id: str
    proposals: tuple[ActionProposal, ...]
    resolved_actions: tuple[ResolvedAction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.world_event_id, str) or not self.world_event_id.strip():
            raise ValueError("world_event_id must not be empty.")
        if isinstance(self.proposals, (str, bytes)):
            raise TypeError("proposals must be a collection of ActionProposal values.")
        proposals = tuple(self.proposals)
        if any(not isinstance(proposal, ActionProposal) for proposal in proposals):
            raise TypeError("proposals must contain only ActionProposal values.")
        if isinstance(self.resolved_actions, (str, bytes)):
            raise TypeError("resolved_actions must be a collection of ResolvedAction values.")
        resolved_actions = tuple(self.resolved_actions)
        if any(not isinstance(action, ResolvedAction) for action in resolved_actions):
            raise TypeError("resolved_actions must contain only ResolvedAction values.")
        proposal_ids = {proposal.proposal_id for proposal in proposals}
        if any(action.action.proposal_id not in proposal_ids for action in resolved_actions):
            raise ValueError("Every resolved action must refer to a proposal in this step.")
        object.__setattr__(self, "proposals", proposals)
        object.__setattr__(self, "resolved_actions", resolved_actions)
