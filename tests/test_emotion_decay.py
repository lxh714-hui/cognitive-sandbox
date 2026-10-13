from cognitive_sandbox.emotion import EmotionalState, EmotionDecay


def test_short_lived_surprise_decays_faster_than_guilt():
    before = EmotionalState(surprise=.8, guilt=.8, fear=.8)
    after = EmotionDecay().apply(before, 1)
    assert after.surprise < after.fear < after.guilt
    assert after.guilt > .79
    assert after.surprise < .6
