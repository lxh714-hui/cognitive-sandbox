from cognitive_sandbox.application.character_state_summary import CharacterStateSummaryBuilder
from cognitive_sandbox.goal.character_goal import CharacterGoal


def test_summary_uses_existing_goal_and_recent_interpretation():
    goal = CharacterGoal("liuyiyi", "寻找异常线索", "investigate", priority=.8)
    summary = CharacterStateSummaryBuilder().build(
        "liuyiyi", goals=(goal,), recent_thoughts=(type("Thought", (), {"interpretation": "传闻来源不稳定"})(),)
    )
    assert summary.current_goal == "寻找异常线索"
    assert summary.current_stage == "重新理解近期经历"
    assert summary.recent_change == "传闻来源不稳定"
