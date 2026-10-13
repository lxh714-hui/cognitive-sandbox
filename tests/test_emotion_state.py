from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.emotion import EmotionalState


def test_emotional_state_has_continuous_bounded_fields_and_is_immutable():
    state = EmotionalState(fear=.7, guilt=.9, curiosity=.8, attachment=.5, stress=.6)
    assert state.fear == .7
    assert state.guilt == .9
    assert len(state.as_dict()) == 17
    with pytest.raises(FrozenInstanceError):
        state.fear = .2
    with pytest.raises(ValueError):
        EmotionalState(anger=1.1)
