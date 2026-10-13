from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.character_presence import CharacterPresence, EntryRule, PresenceManager, PresenceState
from cognitive_sandbox.narrative.conflict_detector import ConflictDetector
from cognitive_sandbox.narrative.event_planner import CandidateEvent, EventPlanner


def test_event_planner_returns_candidates_with_conflict_sources_not_world_events():
    goals = (CharacterGoal("liang", "调查真相", "investigate"), CharacterGoal("song", "隐藏真相", "conceal"))
    conflict = ConflictDetector().detect(goals)[0]
    manager = PresenceManager((
        CharacterPresence("liang", "station", PresenceState.ACTIVE, PresenceState.ACTIVE),
        CharacterPresence("song", "archive", PresenceState.ACTIVE, PresenceState.ACTIVE),
    ))
    candidates = EventPlanner().plan((conflict,), presence=manager.presences, current_time="day-2")
    assert len(candidates) == 1
    assert isinstance(candidates[0], CandidateEvent)
    assert candidates[0].source_conflicts == (conflict.conflict_id,)
    assert "after:day-2" in candidates[0].conditions
    assert candidates[0].location in {"station", "archive"}
    assert any(condition.startswith("participants_must_travel_to:") for condition in candidates[0].conditions)


def test_unknown_characters_are_not_added_as_present_candidates():
    goals = (CharacterGoal("a", "调查真相", "investigate"), CharacterGoal("b", "隐藏真相", "conceal"))
    conflict = ConflictDetector().detect(goals)[0]
    candidates = EventPlanner().plan((conflict,), presence=(CharacterPresence("a"), CharacterPresence("b")))
    assert candidates == ()


def test_planner_can_derive_candidates_from_world_goals_and_pressure():
    goals = (CharacterGoal("doctor", "寻找药品", "collect_medicine"),
             CharacterGoal("merchant", "囤积药品", "hoard_medicine"))
    present = (CharacterPresence("doctor", "clinic", PresenceState.ACTIVE, PresenceState.ACTIVE),
               CharacterPresence("merchant", "market", PresenceState.ACTIVE, PresenceState.ACTIVE))
    candidates = EventPlanner().plan_from_state(goals, world_state={"danger_level": 0.4}, presence=present)
    assert candidates
    assert candidates[0].event_type == "resource_opportunity"
    assert candidates[0].source_conflicts
