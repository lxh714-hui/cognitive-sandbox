from cognitive_sandbox.encounter import (
    EncounterEvaluator, EncounterGenerator, EncounterStatus, EncounterTrajectory,
)


def test_co_located_actions_create_available_candidate_with_score():
    first = EncounterTrajectory("liangjing", "observe", "store", "2026-01-01T20:00:00+00:00", "e1", "观察周围")
    second = EncounterTrajectory("liuyiyi", "investigate", "store", "2026-01-01T20:30:00+00:00", "e2", "调查线索")
    candidate = EncounterGenerator().generate(first, second)
    evaluated = EncounterEvaluator().evaluate(candidate, social_density=.8, narrative_pressure=.3)
    assert evaluated.status is EncounterStatus.AVAILABLE
    assert evaluated.score > .45
    assert evaluated.source_event_ids == ("e1", "e2")


def test_different_place_or_time_is_not_available():
    first = EncounterTrajectory("a", "observe", "home", "2026-01-01T10:00:00+00:00", "e1")
    second = EncounterTrajectory("b", "observe", "market", "2026-01-02T10:00:00+00:00", "e2")
    candidate = EncounterGenerator().generate(first, second)
    assert EncounterEvaluator().evaluate(candidate).status is EncounterStatus.REJECTED
