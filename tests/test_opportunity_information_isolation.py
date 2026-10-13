from datetime import datetime, timezone

from cognitive_sandbox.narrative.opportunity import EventEmergenceEvaluator, OpportunityManager


def test_information_opportunity_is_scoped_to_the_owner_and_does_not_quote_hidden_content():
    manager = OpportunityManager(EventEmergenceEvaluator())
    manager.refresh(
        world_time=datetime(2026, 5, 1, tzinfo=timezone.utc),
        information_by_character={
            "liangjing": ({"content": "有人进入地下室", "confidence": .9},),
            "pei": ({"content": "秘密实验记录", "confidence": .9},),
        },
    )
    liang = manager.visible_to("liangjing")
    pei = manager.visible_to("pei")
    assert liang and pei
    assert all(item.related_character == "liangjing" for item in liang)
    assert all(item.related_character == "pei" for item in pei)
    assert all("地下室" not in item.description and "实验记录" not in item.description
               for item in (*liang, *pei))
    assert manager.visible_to("song") == ()
