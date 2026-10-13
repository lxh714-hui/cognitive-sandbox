from cognitive_sandbox.agency.agency_evaluator import AgencyEvaluator


def test_stagnation_downranks_repeated_failed_strategy_and_favors_alternatives():
    feedback = tuple(("liuyiyi", "investigate", f"2026-06-{day:02d}T09:00:00+00:00",
                      "no_new_information", .1) for day in range(1, 5))
    investigator = AgencyEvaluator.score_action(
        .6, action_type="investigate", feedback=feedback, goal_stagnation=.8,
    )
    social = AgencyEvaluator.score_action(
        .6, action_type="socialize", feedback=feedback, goal_stagnation=.8,
    )
    assert investigator < social


def test_stagnation_only_changes_candidate_scores_and_does_not_force_action():
    stable = AgencyEvaluator.score_action(.5, action_type="investigate", goal_stagnation=0)
    stagnant = AgencyEvaluator.score_action(.5, action_type="investigate", goal_stagnation=.9)
    # No failure history means stagnation alone cannot force an action or
    # suppress a viable strategy; it only adjusts ranked candidate scores.
    assert 0 <= stable <= 1
    assert 0 <= stagnant <= 1
