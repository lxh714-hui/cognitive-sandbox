from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from cognitive_sandbox.application.branch_generator import BranchGenerator
from cognitive_sandbox.application.branch_scorer import BranchScorer
from cognitive_sandbox.application.branch_value_evaluator import BranchValueEvaluator
from cognitive_sandbox.application.search_priority import SearchPriorityCalculator
from cognitive_sandbox.domain.actions import ActionCandidate
from cognitive_sandbox.domain.story import (
    BranchValue,
    BranchScore,
    NarrativeSearchResult,
    SearchPolicy,
    SearchStrategy,
    StoryBranch,
)


class NarrativeSearch:
    """Run a bounded metadata-only search over candidate-driven story branches."""

    def __init__(
        self,
        candidate_provider: Callable[[StoryBranch], Iterable[ActionCandidate]],
        *,
        branch_value_evaluator: BranchValueEvaluator,
        priority_calculator: SearchPriorityCalculator | None = None,
        branch_generator: BranchGenerator | None = None,
        branch_scorer: BranchScorer | None = None,
        search_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not callable(candidate_provider):
            raise TypeError("candidate_provider must be callable.")
        if not callable(getattr(branch_value_evaluator, "evaluate", None)):
            raise TypeError("branch_value_evaluator must provide an evaluate method.")
        self._candidate_provider = candidate_provider
        self._branch_generator = branch_generator or BranchGenerator()
        self._branch_scorer = branch_scorer or BranchScorer()
        self._branch_value_evaluator = branch_value_evaluator
        self._priority_calculator = priority_calculator or SearchPriorityCalculator()
        self._search_id_factory = search_id_factory or (lambda: str(uuid4()))

    def search(self, root_branch: StoryBranch, policy: SearchPolicy) -> NarrativeSearchResult:
        if not isinstance(root_branch, StoryBranch):
            raise TypeError("root_branch must be a StoryBranch.")
        if not isinstance(policy, SearchPolicy):
            raise TypeError("policy must be a SearchPolicy.")

        generated: list[StoryBranch] = []
        depths: dict[str, int] = {}
        scores: dict[str, BranchScore] = {}
        values: dict[str, BranchValue] = {}
        expanded: list[str] = []
        known_ids = {root_branch.branch_id}
        # Queue entries retain insertion order, which makes score-guided ties
        # stable and keeps behavior deterministic for every strategy.
        frontier: list[tuple[StoryBranch, int]] = [(root_branch, 0)]

        while frontier and len(generated) + 1 < policy.max_nodes:
            if policy.strategy is SearchStrategy.BREADTH_FIRST:
                branch, depth = frontier.pop(0)
            elif policy.strategy is SearchStrategy.DEPTH_FIRST:
                branch, depth = frontier.pop()
            else:
                best_index = max(
                    range(len(frontier)),
                    key=lambda index: (
                        self._search_priority(frontier[index][0], values),
                        -index,
                    ),
                )
                branch, depth = frontier.pop(best_index)

            if depth >= policy.max_depth:
                continue
            expanded.append(branch.branch_id)
            remaining = policy.max_nodes - len(generated) - 1
            candidates = self._candidate_provider(branch)
            if isinstance(candidates, (str, bytes)):
                raise TypeError("candidate_provider must return ActionCandidate values.")
            candidates = tuple(candidates)
            if any(not isinstance(candidate, ActionCandidate) for candidate in candidates):
                raise TypeError("candidate_provider must return ActionCandidate values.")
            candidates = candidates[: min(policy.max_branches_per_node, remaining)]
            children = self._branch_generator.generate(
                branch,
                candidates,
                divergence_event_id=branch.divergence_event_id,
            )
            for child in children:
                if child.branch_id in known_ids:
                    raise ValueError("Branch IDs must be unique throughout one search.")
                known_ids.add(child.branch_id)
                generated.append(child)
                child_depth = depth + 1
                depths[child.branch_id] = child_depth
                branch_score = self._branch_scorer.score(child)
                if not isinstance(branch_score, BranchScore):
                    raise TypeError("branch_scorer.score must return a BranchScore.")
                branch_value = self._branch_value_evaluator.evaluate(child, branch_score)
                if not isinstance(branch_value, BranchValue):
                    raise TypeError("branch_value_evaluator.evaluate must return a BranchValue.")
                if branch_value.branch_id != child.branch_id:
                    raise ValueError("BranchValue must belong to the evaluated branch.")
                scores[child.branch_id] = branch_score
                values[child.branch_id] = branch_value
                frontier.append((child, child_depth))

        best_branch_id = None
        if generated:
            best_branch_id = min(
                generated,
                key=lambda item: (
                    -self._search_priority(item, values)
                    if policy.strategy is SearchStrategy.SCORE_GUIDED
                    else -scores[item.branch_id].score,
                    item.branch_id,
                ),
            ).branch_id
        return NarrativeSearchResult(
            search_id=self._search_id_factory(),
            root_branch_id=root_branch.branch_id,
            strategy=policy.strategy,
            generated_branches=tuple(generated),
            expanded_branch_ids=tuple(expanded),
            branch_scores=tuple(scores[branch.branch_id] for branch in generated),
            best_branch_id=best_branch_id,
            depth_reached=max(depths.values(), default=0),
            branch_values=tuple(values[branch.branch_id] for branch in generated),
        )

    def _search_priority(
        self,
        branch: StoryBranch,
        values: dict[str, BranchValue],
    ) -> float:
        branch_value = values.get(branch.branch_id, BranchValue(branch.branch_id, 0.5, ()))
        action = branch.divergence_action
        confidence = 1.0 if action is None else action.metadata.get("confidence", 1.0)
        return self._priority_calculator.calculate(branch_value, confidence)
