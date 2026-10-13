from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader
from cognitive_sandbox.narrative.narrative_thread import NarrativeThreadStatus


def test_anchor_starts_with_non_linear_narrative_threads():
    threads = {item.id: item for item in AnchorWorldLoader().load().narrative_state.threads}
    assert threads["liangjing_return"].status is NarrativeThreadStatus.ACTIVE
    assert threads["liangjing_return"].participants == ("liangjing",)
    assert threads["anomaly_investigation"].status is NarrativeThreadStatus.DORMANT
    assert threads["anomaly_investigation"].participants == ("liuyiyi", "song")
    assert threads["potential_intersection"].status is NarrativeThreadStatus.POSSIBLE
    assert threads["potential_intersection"].participants == ("liangjing", "liuyiyi", "pei")
