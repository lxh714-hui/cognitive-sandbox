from cognitive_sandbox.agency.goal_action_generator import GoalActionGenerator
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.cognition.cognitive_style import CognitiveStyle


def test_investigation_goal_generates_candidates_from_only_visible_clues():
    goal = CharacterGoal("liuyiyi", "寻找异常线索", "investigate_anomaly", .7)
    generator = GoalActionGenerator()
    hidden_only = generator.generate(goal, (), character_id="liuyiyi")
    assert not any(item.action.action_type == "investigate" for item in hidden_only)
    visible = generator.generate(
        goal, ("附近有几处时间记录对不上的线索",), (),
        {"curiosity": .9}, {"cognitive_style": CognitiveStyle(suspicious=.8, analytical=.8)},
        character_id="liuyiyi", current_location="neighborhood",
    )
    assert visible[0].action.action_type == "investigate"
    assert visible[0].action.parameters["location"] == "neighborhood"
    assert all(item.action.actor_id == "liuyiyi" for item in visible)


def test_everyday_goal_generates_work_socialize_and_organize_options():
    goal = CharacterGoal("liangjing", "重新开始生活", "maintain", .6)
    actions = GoalActionGenerator().generate(goal, character_id="liangjing")
    assert {item.action.action_type for item in actions} >= {"work", "socialize", "organize"}


def test_public_motivation_and_owned_relationship_adjust_social_candidate():
    from cognitive_sandbox.motivation.character_motivation import MotivationView
    from cognitive_sandbox.relationship.relationship_state import RelationshipState

    goal = CharacterGoal("pei", "维持日常生活", "maintain", .5)
    generator = GoalActionGenerator()
    low = generator.generate(goal, character_id="pei")
    high = generator.generate(
        goal, relationships=(RelationshipState("pei", "neighbor", trust=80, affinity=60),),
        character_id="pei", motivation=MotivationView("pei", "维持日常生活"),
    )
    low_social = next(item.score for item in low if item.action.action_type == "socialize")
    high_social = next(item.score for item in high if item.action.action_type == "socialize")
    assert high_social > low_social


def test_observe_changes_goal_generates_observation_not_investigation():
    goal = CharacterGoal("song", "观察周围变化", "observe_changes", .6)
    actions = GoalActionGenerator().generate(
        goal, ("有数次相似的异常记录",), character_id="song",
    )
    assert actions[0].action.action_type == "observe"
    assert not any(item.action.action_type == "investigate" for item in actions)
