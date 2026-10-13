import pytest

from cognitive_sandbox.identity import CharacterIdentity, IdentityManager


def test_rename_changes_display_identity_but_keeps_permanent_id_and_alias():
    identities = IdentityManager((CharacterIdentity("char_01", "旧名", "旧名", editable=True),))
    updated = identities.rename_character("char_01", "新名")
    assert updated.character_id == "char_01"
    assert updated.display_name == "新名"
    assert updated.original_name == "旧名"
    assert "旧名" in updated.aliases
    assert identities.display_name_for("char_01") == "新名"


def test_identity_edit_does_not_touch_other_domain_state_and_respects_package_lock():
    manager = IdentityManager((
        CharacterIdentity("fixed", "包内名", "包内名", editable=False, naming_source="world_package"),
    ))
    with pytest.raises(PermissionError):
        manager.rename_character("fixed", "改名")
    with pytest.raises(KeyError):
        manager.rename_character("unknown", "Name")


def test_renaming_does_not_change_event_history_identity():
    from cognitive_sandbox.domain.world_events import WorldEvent
    from cognitive_sandbox.history.event_timeline import EventTimeline

    manager = IdentityManager((CharacterIdentity("char_01", "旧名", "旧名"),))
    timeline = EventTimeline()
    event = WorldEvent("event-1", "main", "w", "help_attempt", "char_01", {}, 1)
    timeline.record_event(event)
    manager.rename_character("char_01", "新名")
    record = timeline.events[0]
    assert record.actor_ids == ("char_01",)
    assert manager.display_name_for(record.actor_ids[0]) == "新名"
