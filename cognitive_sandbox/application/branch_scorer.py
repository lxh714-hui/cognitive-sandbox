from cognitive_sandbox.domain.story import BranchScore, StoryBranch


class BranchScorer:
    """Read an optional deterministic score hint from candidate metadata."""

    def score(self, branch: StoryBranch) -> BranchScore:
        if not isinstance(branch, StoryBranch):
            raise TypeError("branch must be a StoryBranch.")
        metadata = branch.divergence_action.metadata if branch.divergence_action else {}
        value = metadata.get("score", 0.5)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("candidate score metadata must be a number between 0 and 1.")
        if not 0 <= value <= 1:
            raise ValueError("candidate score metadata must be between 0 and 1.")
        reason = "candidate score hint" if "score" in metadata else "neutral default score"
        return BranchScore(branch.branch_id, float(value), (reason,))
