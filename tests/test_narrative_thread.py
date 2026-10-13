from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.narrative.conflict_detector import ConflictDetector
from cognitive_sandbox.narrative.narrative_pressure import NarrativePressureCalculator
from cognitive_sandbox.narrative.narrative_state import NarrativeState
from cognitive_sandbox.narrative.narrative_thread import NarrativeThread, NarrativeThreadStatus


def test_goal_conflict_can_become_an_explainable_story_thread():
    goals = (
        CharacterGoal("liang", "调查异常并寻找真相", "investigate", 0.8),
        CharacterGoal("song", "隐藏真相并阻止调查", "conceal_truth", 0.7),
    )
    conflicts = ConflictDetector().detect(goals)
    assert conflicts[0].conflict_type == "information_conflict"
    generated = ConflictDetector().generate_threads(conflicts)
    assert generated[0].participants == ("liang", "song")
    thread = NarrativeThread("thread1", "异常调查", conflicts[0].participants, conflicts[0].description,
                             pressure=conflicts[0].pressure, status=NarrativeThreadStatus.ACTIVE,
                             conflict_sources=conflicts[0].sources)
    state = NarrativeState().with_thread(thread)
    assert state.threads == (thread,)
    assert state.threads[0].conflict_sources == (goals[0].goal_id, goals[1].goal_id)


def test_pressure_is_bounded_and_reports_trend():
    detector = ConflictDetector()
    goals = (CharacterGoal("a", "寻找真相", "investigate"), CharacterGoal("b", "隐藏真相", "conceal"))
    pressure = NarrativePressureCalculator().calculate(detector.detect(goals), danger=0.8)
    assert 0 <= pressure.urgency <= 1
    assert pressure.trend == "stable"
