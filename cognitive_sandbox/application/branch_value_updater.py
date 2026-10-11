from cognitive_sandbox.application.branch_evaluation_feedback import BranchEvaluationFeedback
from cognitive_sandbox.domain.story import BranchEvaluationSummary, BranchValue


class BranchValueUpdater:
    """Blend an initial static branch value with one simulation feedback item."""

    OLD_VALUE_WEIGHT = 0.5
    FEEDBACK_WEIGHT = 0.5

    def update(
        self,
        branch_value: BranchValue,
        feedback: BranchEvaluationFeedback | BranchEvaluationSummary,
    ) -> BranchValue:
        if not isinstance(branch_value, BranchValue):
            raise TypeError("branch_value must be a BranchValue.")
        if not isinstance(feedback, (BranchEvaluationFeedback, BranchEvaluationSummary)):
            raise TypeError("feedback must be BranchEvaluationFeedback or BranchEvaluationSummary.")
        if branch_value.branch_id != feedback.branch_id:
            raise ValueError("feedback must belong to the branch value being updated.")

        if isinstance(feedback, BranchEvaluationSummary):
            feedback_score = (
                feedback.success_rate * 0.5 + feedback.average_soft_score * 0.5
            )
            weighted_feedback = (
                feedback_score * feedback.confidence
                + branch_value.value * (1 - feedback.confidence)
            )
            updated = branch_value.value * 0.5 + weighted_feedback * 0.5
            reason = (
                "aggregated simulation feedback: "
                f"success_rate={feedback.success_rate:.3f}, "
                f"average_soft_score={feedback.average_soft_score:.3f}, "
                f"confidence={feedback.confidence:.3f}"
            )
        else:
            feedback_score = feedback.soft_score if feedback.success else feedback.soft_score * 0.5
            updated = (
                branch_value.value * self.OLD_VALUE_WEIGHT
                + feedback_score * self.FEEDBACK_WEIGHT
            )
            reason = f"simulation feedback: {feedback.reason}"
        updated = max(0.0, min(1.0, updated))
        return BranchValue(
            branch_id=branch_value.branch_id,
            value=updated,
            reasons=(*branch_value.reasons, reason),
        )
