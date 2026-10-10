from cognitive_sandbox.domain.models import ConversationEvent
from cognitive_sandbox.infrastructure.sqlite_store import SQLiteEventStore


def test_events_round_trip_and_are_scoped_to_world(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.sqlite3")
    first = ConversationEvent("e1", "w1", "a1", "player", "你好", metadata={"turn": 1})
    second = ConversationEvent("e2", "w2", "a2", "player", "elsewhere")

    store.append(first)
    store.append(second)

    assert store.list_for_world("w1") == [first]
    assert store.list_for_world("w2") == [second]
