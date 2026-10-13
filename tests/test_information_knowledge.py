from cognitive_sandbox.information import InformationManager
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.domain.world_events import WorldEvent


def test_received_information_is_character_scoped_and_provenanced():
    store = KnowledgeStore()
    manager = InformationManager(knowledge_store=store)
    manager.handle_event(WorldEvent("e", event_type="public_report", actor_id="liuyiyi",
                                    payload={"description": "街区有人听到异响", "importance": .7},
                                    timestamp="t1"))
    own = store.query("liuyiyi")
    assert len(own) == 1
    record, fact = own[0]
    assert record.knowledge_type.value == "OBSERVED"
    assert fact.fact_type == "clue"
    assert store.query("liangjing") == ()
    assert manager.received_for("liuyiyi")[0]["source"] == "亲历事件形成的线索"


def test_direct_participants_get_distinct_records_from_the_event():
    store = KnowledgeStore()
    manager = InformationManager(knowledge_store=store)
    manager.handle_event(WorldEvent("e", event_type="report", actor_id="a", target_id="b",
                                    payload={"description": "看见灯光闪烁"}, timestamp="t1"))
    assert len(store.query("a")) == len(store.query("b")) == 1
