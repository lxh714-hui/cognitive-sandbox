from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader
from cognitive_sandbox.application.game_launcher import GameLauncher


def test_anchor_initial_knowledge_is_private_per_character():
    session = GameLauncher().start_anchor_world()
    store = session.knowledge_store
    liangjing = {record.known_content for record, _fact in store.query("liangjing")}
    liuyiyi = {record.known_content for record, _fact in store.query("liuyiyi")}
    song = {record.known_content for record, _fact in store.query("song")}
    pei = {record.known_content for record, _fact in store.query("pei")}
    configured = AnchorWorldLoader().load().initial_knowledge
    assert liangjing == {item["content"] for item in configured["liangjing"]}
    assert liuyiyi == {item["content"] for item in configured["liuyiyi"]}
    assert song == {item["content"] for item in configured["song"]}
    assert pei == {item["content"] for item in configured["pei"]}
    # Each query returns only records owned by that character; private facts
    # for another role are not retrievable through the ordinary interface.
    for owner, records in (("liangjing", liangjing), ("liuyiyi", liuyiyi), ("song", song), ("pei", pei)):
        assert all(record.owner_id == owner for record, _fact in store.query(owner))
