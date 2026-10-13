from cognitive_sandbox.agency.agency_evaluator import AgencyEvaluator
from cognitive_sandbox.agency.agency_state import AgencyState, AgencyStateManager


def test_action_result_and_effectiveness_are_kept_in_immutable_snapshot():
    manager = AgencyStateManager()
    manager.record_action("npc", "investigate", "2026-10-13T12:00:00+00:00",
                          result="no_new_information", effectiveness=.2)
    state = manager.snapshot()
    assert state.action_feedback_history[0][3:] == ("no_new_information", .2)
    restored = AgencyState(state.agencies, state.routine_progress,
                           state.autonomous_action_history, state.action_feedback_history)
    assert restored.action_feedback_history == state.action_feedback_history


def test_ineffective_repeats_reduce_candidate_score():
    feedback = tuple(("npc", "investigate", f"2026-10-{day:02d}T12:00:00+00:00", "no_new_information", .2)
                     for day in (11, 12, 13))
    repeated = AgencyEvaluator.score_action(.6, action_type="investigate", feedback=feedback,
                                            current_time="2026-10-13T13:00:00+00:00")
    alternative = AgencyEvaluator.score_action(.6, action_type="organize", feedback=feedback,
                                               current_time="2026-10-13T13:00:00+00:00")
    assert alternative > repeated
