from cognitive_sandbox.application.anchor_world_loader import AnchorWorldLoader


def test_anchor_package_loads_location_relations_routines_and_background_information():
    package = AnchorWorldLoader().load()
    assert package.world_card.content_version == "0.2"
    assert len(package.location_relations) >= 4
    assert all(0 <= item["information_flow"] <= 1 for item in package.location_relations)
    assert {"liangjing", "liuyiyi", "song", "pei"} <= set(package.routines)
    assert any(item.event_type == "neighborhood_rumor" for item in package.scenario_content.event_cards)
