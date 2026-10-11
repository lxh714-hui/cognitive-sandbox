from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import BranchGenerationResult, StoryBranch


class BranchGenerator:
    """Create one metadata-only story route for each candidate action."""

    def __init__(
        self,
        *,
        branch_id_factory: Callable[[], str] | None = None,
        generation_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._branch_id_factory = branch_id_factory or (lambda: str(uuid4()))
        self._generation_id_factory = generation_id_factory or (lambda: str(uuid4()))

    def generate(
        self,
        source_branch: StoryBranch,
        candidates: Iterable[ActionCandidate],
        *,
        divergence_event_id: str | None = None,
    ) -> tuple[StoryBranch, ...]:
        branches, _ = self.generate_with_result(
            source_branch,
            candidates,
            divergence_event_id=divergence_event_id,
        )
        return branches

    def generate_with_result(
        self,
        source_branch: StoryBranch,
        candidates: Iterable[ActionCandidate],
        *,
        divergence_event_id: str | None = None,
    ) -> tuple[tuple[StoryBranch, ...], BranchGenerationResult]:
        if not isinstance(source_branch, StoryBranch):
            raise TypeError("source_branch must be a StoryBranch.")
        if divergence_event_id is not None and (
            not isinstance(divergence_event_id, str) or not divergence_event_id.strip()
        ):
            raise ValueError("divergence_event_id must be None or a non-empty string.")
        if isinstance(candidates, (str, bytes)):
            raise TypeError("candidates must be an iterable of ActionCandidate values.")
        candidates = tuple(candidates)
        if any(not isinstance(candidate, ActionCandidate) for candidate in candidates):
            raise TypeError("candidates must contain only ActionCandidate values.")

        branch_ids = tuple(self._branch_id_factory() for _ in candidates)
        if any(not isinstance(branch_id, str) or not branch_id.strip() for branch_id in branch_ids):
            raise ValueError("branch_id_factory must return non-empty strings.")
        if len(set(branch_ids)) != len(branch_ids) or source_branch.branch_id in branch_ids:
            raise ValueError("Generated branch IDs must be unique and differ from the source branch.")
        branches = tuple(
            StoryBranch(
                branch_id=branch_id,
                parent_branch_id=source_branch.branch_id,
                world_id=source_branch.world_id,
                revision=source_branch.revision,
                divergence_event_id=divergence_event_id,
                divergence_action=candidate,
            )
            for branch_id, candidate in zip(branch_ids, candidates, strict=True)
        )
        result = BranchGenerationResult(
            generation_id=self._generation_id_factory(),
            source_branch_id=source_branch.branch_id,
            created_branches=branch_ids,
        )
        return branches, result
