from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    BranchExplorationConfig,
    BranchExplorationResult,
    StoryBranch,
)


class BranchExplorer:
    """Expand candidate-driven story branch metadata to a finite configured depth."""

    def __init__(
        self,
        candidate_provider: Callable[[StoryBranch], Iterable[ActionCandidate]],
        *,
        branch_generator: BranchGenerator | None = None,
        exploration_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not callable(candidate_provider):
            raise TypeError("candidate_provider must be callable.")
        self._candidate_provider = candidate_provider
        self._branch_generator = branch_generator or BranchGenerator()
        self._exploration_id_factory = exploration_id_factory or (lambda: str(uuid4()))

    def explore(
        self,
        root_branch: StoryBranch,
        config: BranchExplorationConfig,
    ) -> BranchExplorationResult:
        if not isinstance(root_branch, StoryBranch):
            raise TypeError("root_branch must be a StoryBranch.")
        if not isinstance(config, BranchExplorationConfig):
            raise TypeError("config must be a BranchExplorationConfig.")

        generated: list[StoryBranch] = []
        depths: list[int] = []
        expanded: list[str] = []
        known_ids = {root_branch.branch_id}
        frontier: list[tuple[StoryBranch, int]] = [(root_branch, 0)]

        while frontier:
            next_frontier: list[tuple[StoryBranch, int]] = []
            for parent, depth in frontier:
                if depth >= config.max_depth:
                    continue
                expanded.append(parent.branch_id)
                candidates = self._candidate_provider(parent)
                if isinstance(candidates, (str, bytes)):
                    raise TypeError("candidate_provider must return ActionCandidate values.")
                candidates = tuple(candidates)
                if any(not isinstance(candidate, ActionCandidate) for candidate in candidates):
                    raise TypeError("candidate_provider must return ActionCandidate values.")
                candidates = candidates[: config.max_branches_per_node]
                children = self._branch_generator.generate(
                    parent,
                    candidates,
                    divergence_event_id=parent.divergence_event_id,
                )
                for child in children:
                    if child.branch_id in known_ids:
                        raise ValueError("Branch IDs must be unique throughout one exploration.")
                    known_ids.add(child.branch_id)
                    generated.append(child)
                    depths.append(depth + 1)
                    next_frontier.append((child, depth + 1))
            frontier = next_frontier

        return BranchExplorationResult(
            exploration_id=self._exploration_id_factory(),
            root_branch_id=root_branch.branch_id,
            generated_branches=tuple(generated),
            branch_depths=tuple(depths),
            expanded_branch_ids=tuple(expanded),
            depth_reached=max(depths, default=0),
        )
