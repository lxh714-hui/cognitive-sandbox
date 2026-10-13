from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.emotion import EmotionalMemory, EmotionalState, EmotionModel


def test_emotional_memory_is_immutable_and_changes_future_action_scores():
    memory = EmotionalMemory("e1", {"guilt": .5}, "protective", .8)
    model = EmotionModel()
    state = EmotionalState()
    assert model.score_modifier("protect", state, (memory,)) > model.score_modifier("escape", state)
    with pytest.raises(TypeError):
        memory.emotional_impact["guilt"] = .1
    with pytest.raises(FrozenInstanceError):
        memory.persistence = 0
