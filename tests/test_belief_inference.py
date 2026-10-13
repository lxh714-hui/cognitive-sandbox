import pytest
from dataclasses import FrozenInstanceError

from cognitive_sandbox.cognition import Belief, BeliefInference, CognitiveEngine


def test_belief_is_scoped_and_is_an_interpretation_not_a_fact():
    belief = BeliefInference().infer("npc-a", "fact-door-open", "可能是朋友回来了", .6, .4)
    assert belief.character_id == "npc-a"
    assert belief.source_fact == "fact-door-open"
    assert belief.interpretation.startswith("可能")
    with pytest.raises(FrozenInstanceError):
        belief.confidence = .9
    engine = CognitiveEngine()
    engine.infer_belief("npc-a", "fact-door-open", "可能是朋友回来了")
    assert engine.beliefs["npc-a"][0].character_id == "npc-a"
    assert "npc-a" not in engine.beliefs or not engine.beliefs.get("npc-b")
