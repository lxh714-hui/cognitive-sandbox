from cognitive_sandbox.application.npc.npc_decision_engine import NpcDecisionEngine
from cognitive_sandbox.domain.character_mind import CharacterMind, Identity, KnowledgeContext, PersonalityProfile
from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.goal.character_goal import CharacterGoal
from cognitive_sandbox.motivation import CharacterMotivation


def test_goals_personality_and_pressure_rank_multiple_candidates_differently():
    engine = NpcDecisionEngine()
    event = WorldEvent("e", "main", "w", "anomaly_detected", "player", {"danger": "attack"}, 1)
    knowledge = KnowledgeContext(owner_id="npc")
    curious = CharacterMind(Identity("梁景", "resident"), PersonalityProfile(traits=("curious",)))
    cautious = CharacterMind(Identity("宋", "guard"), PersonalityProfile(traits=("cautious",)))
    goal = CharacterGoal("npc", "调查异常并寻找真相", "investigate", 0.9)
    motives = CharacterMotivation("npc", "调查异常", "寻找真相", "无法接受未知", "被欺骗")

    curious_actions = engine.decide_candidates(curious, knowledge, event, goals=(goal,), motivation=motives, pressure=0.7)
    cautious_actions = engine.decide_candidates(cautious, KnowledgeContext(owner_id="npc"), event, risk=0.9)

    assert len(curious_actions) >= 1
    assert curious_actions[0].action_type == "investigate"
    assert cautious_actions[0].action_type == "escape"


def test_candidate_decisions_are_scoped_and_do_not_submit_world_events():
    engine = NpcDecisionEngine()
    event = WorldEvent("e", "main", "w", "anomaly_detected", "player", {}, 1)
    mind = CharacterMind(Identity("梁景", "resident"), PersonalityProfile())
    actions = engine.decide_candidates(mind, KnowledgeContext(owner_id="npc"), event)
    assert actions and all(action.actor_id == "npc" for action in actions)
    assert not any(isinstance(action, WorldEvent) for action in actions)
