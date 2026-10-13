from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.cognition import AttentionProfile, CognitiveStyle, ReasoningProfile


def test_cognitive_profiles_are_bounded_and_immutable():
    style = CognitiveStyle(analytical=.6, intuitive=.7, suspicious=.8, strategic=.5)
    assert style.analytical == .6
    with pytest.raises(FrozenInstanceError):
        style.analytical = .9
    with pytest.raises(ValueError):
        CognitiveStyle(analytical=1.1)
    with pytest.raises(ValueError):
        ReasoningProfile(reasoning_depth=-.1)
    assert AttentionProfile(risk_signal=.9).risk_signal == .9
