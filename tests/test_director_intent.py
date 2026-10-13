from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.director import DirectorIntent, DirectorIntentParser, DirectorIntentType


def test_natural_language_parses_entry_and_meeting_targets():
    parser = DirectorIntentParser()
    known = (("liuyiyi", "柳依依"), ("liangjing", "梁景"))
    entry = parser.parse("希望柳依依早点出现", known)
    meeting = parser.parse("希望梁景与柳依依相遇", known)
    assert entry.intent_type is DirectorIntentType.CHARACTER_ENTRY
    assert entry.target == "liuyiyi"
    assert meeting.intent_type is DirectorIntentType.CHARACTER_MEETING
    assert set(meeting.target.split(",")) == {"liangjing", "liuyiyi"}
    with pytest.raises(FrozenInstanceError):
        entry.priority = .1


def test_intent_rejects_invalid_priority():
    with pytest.raises(ValueError):
        DirectorIntent(DirectorIntentType.CUSTOM_DIRECTION, None, "推动剧情", 1.2)
