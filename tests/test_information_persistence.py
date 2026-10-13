from cognitive_sandbox.information import InformationManager, InformationSnapshot
from cognitive_sandbox.knowledge.storage.knowledge_store import KnowledgeStore
from cognitive_sandbox.persistence.world_serializer import WorldSerializer
from cognitive_sandbox.domain.world_events import WorldEvent


def test_information_snapshot_round_trips_and_legacy_defaults_are_empty():
    manager = InformationManager(knowledge_store=KnowledgeStore())
    manager.handle_event(WorldEvent("e", event_type="report", actor_id="a",
                                    payload={"description": "街区传来异响"}, timestamp="t"))
    serializer = WorldSerializer()
    encoded = serializer._encode(manager.snapshot())
    restored = serializer._decode(encoded)
    assert isinstance(restored, InformationSnapshot)
    assert restored.network.clues == manager.clues
    assert restored.network.processed_event_ids == ("e",)
    assert InformationManager(knowledge_store=KnowledgeStore(), snapshot=InformationSnapshot()).clues == ()
