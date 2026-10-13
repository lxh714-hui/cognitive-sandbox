from cognitive_sandbox.agency.goal_action_generator import GoalActionGenerator
from cognitive_sandbox.goal.character_goal import CharacterGoal


def test_scenario_rules_generate_actions_only_from_visible_knowledge():
    goal = CharacterGoal("agent", "寻找线索", "investigate", .7)
    generator = GoalActionGenerator((
        {"goal_type": "investigate", "action_type": "investigate", "score": .8,
         "minimum_visible_knowledge": 1, "parameters": {"location": "$current_location"}},
        {"goal_type": "investigate", "action_type": "organize", "score": .6,
         "minimum_visible_knowledge": 1},
    ))
    hidden_only = generator.generate(goal, (), character_id="agent", current_location="site")
    assert hidden_only == ()
    visible = generator.generate(goal, ("visible clue",), character_id="agent", current_location="site")
    assert visible[0].action.action_type == "investigate"
    assert visible[0].action.parameters["location"] == "site"
    assert {item.action.action_type for item in visible} == {"investigate", "organize"}


def test_scenario_may_configure_multiple_daily_actions_without_engine_goal_semantics():
    goal = CharacterGoal("agent", "daily routine", "daily_goal", .6)
    generator = GoalActionGenerator(tuple(
        {"goal_type": "daily_goal", "action_type": action, "score": .5}
        for action in ("work", "socialize", "organize")
    ))
    actions = generator.generate(goal, character_id="agent")
    assert {item.action.action_type for item in actions} == {"work", "socialize", "organize"}


def test_unknown_scenario_goal_has_no_embedded_action_mapping():
    goal = CharacterGoal("agent", "arbitrary goal", "unconfigured_goal", .6)
    assert GoalActionGenerator().generate(goal, character_id="agent") == ()
