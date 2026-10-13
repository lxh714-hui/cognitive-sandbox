from cognitive_sandbox.agency.agency_evaluator import AgencyEvaluator
from cognitive_sandbox.conflict import ConflictManager, ConflictState, ConflictType
from cognitive_sandbox.emotion.emotional_state import EmotionalState


def test_conflict_shifts_candidate_scores_without_selecting_or_forcing_action():
    conflict = ConflictState("c", ConflictType.GOAL_CONFLICT, ("a", "b"), severity=.7)
    calm = AgencyEvaluator.conflict_response_score("ask", conflicts=(conflict,))
    fearful = AgencyEvaluator.conflict_response_score("ask", conflicts=(conflict,), emotion=EmotionalState(fear=.9))
    avoiding = AgencyEvaluator.conflict_response_score("rest", conflicts=(conflict,), emotion=EmotionalState(fear=.9))
    assert calm > fearful
    assert avoiding > 0
    assert ConflictManager().active_conflicts == ()
