from __future__ import annotations

from collections.abc import Iterable

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import ExpansionPolicy, StoryBranch


class LazyExpander:
    """Limit branch creation per call and across the lifetime of this expander."""

    def __init__(self, branch_generator: BranchGenerator | None = None) -> None:
        self._branch_generator = branch_generator or BranchGenerator()
        self._total_expansions = 0

    @property
    def total_expansions(self) -> int:
        return self._total_expansions

    def expand(
        self,
        branch: StoryBranch,
        candidates: Iterable[ActionCandidate],
        policy: ExpansionPolicy,
    ) -> tuple[StoryBranch, ...]:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        if not isinstance(policy, ExpansionPolicy):
            raise TypeError("policy must be an ExpansionPolicy.")
        if isinstance(candidates, (str, bytes)):
            raise TypeError("candidates must be an iterable of ActionCandidate values.")
        candidate_list = tuple(candidates)
        if any(not isinstance(candidate, ActionCandidate) for candidate in candidate_list):
            raise TypeError("candidates must contain only ActionCandidate values.")

        remaining_total = policy.max_total_expansions - self._total_expansions
        limit = min(policy.max_branches_per_expansion, max(0, remaining_total))
        selected = candidate_list[:limit]
        if not selected:
            return ()

        children = self._branch_generator.generate(
            branch,
            selected,
            divergence_event_id=branch.divergence_event_id,
        )
        self._total_expansions += len(children)
        return children
