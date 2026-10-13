from cognitive_sandbox.agency.agency_evaluator import AgencyEvaluator


def test_recent_repeated_action_loses_to_a_novel_action():
    actions = tuple(("npc", "investigate", f"2026-10-{day:02d}T12:00:00+00:00") for day in (10, 11, 12))
    repeated = AgencyEvaluator.score_action(.6, action_type="investigate", recent_actions=actions,
                                            current_time="2026-10-13T12:00:00+00:00")
    novel = AgencyEvaluator.score_action(.6, action_type="socialize", recent_actions=actions,
                                         current_time="2026-10-13T12:00:00+00:00")
    assert novel > repeated


def test_old_repetition_does_not_permanently_penalize_action():
    old = (("npc", "observe", "2026-09-01T12:00:00+00:00"),)
    score = AgencyEvaluator.score_action(.5, action_type="observe", recent_actions=old,
                                         current_time="2026-10-13T12:00:00+00:00")
    assert score > .5


