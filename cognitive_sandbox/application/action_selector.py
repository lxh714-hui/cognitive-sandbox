from __future__ import annotations

from collections.abc import Sequence

from cognitive_sandbox.domain.actions import ActionCandidate, ActionScore


class ActionSelector:
    """Choose the highest-scoring candidate, retaining input order for ties."""

    def select(
        self,
        candidates: Sequence[ActionCandidate],
        scores: Sequence[ActionScore],
    ) -> tuple[ActionCandidate, ActionScore] | None:
        if len(candidates) != len(scores):
            raise ValueError("Each action candidate must have exactly one score.")
        if not candidates:
            return None
        for candidate, score in zip(candidates, scores, strict=True):
            if not isinstance(candidate, ActionCandidate):
                raise TypeError("candidates must contain ActionCandidate values.")
            if not isinstance(score, ActionScore):
                raise TypeError("scores must contain ActionScore values.")
            if candidate.action_type != score.action_type:
                raise ValueError("Candidate and score action types must match by position.")
        selected_index = max(range(len(scores)), key=lambda index: scores[index].score)
        return candidates[selected_index], scores[selected_index]
