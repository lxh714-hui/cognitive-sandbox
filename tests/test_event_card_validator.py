from cognitive_sandbox.application.event_card_validator import EventCardValidator
from cognitive_sandbox.domain.event_card import EventCard


def test_event_card_validator_accepts_complete_card():
    card = EventCard(
        "hospital_power_failure",
        "医院停电",
        "医院备用电源即将耗尽",
        "initial",
        ("doctor", "player"),
        ("night",),
        ("hospital_dark",),
        1,
    )

    result = EventCardValidator().validate(card)

    assert result.valid
    assert result.errors == ()


def test_event_card_validator_reports_invalid_values_without_mutating_card():
    card = object.__new__(EventCard)
    object.__setattr__(card, "event_id", "")
    object.__setattr__(card, "name", "")
    object.__setattr__(card, "description", "停电")
    object.__setattr__(card, "event_type", "")
    object.__setattr__(card, "participants", ["doctor"])
    object.__setattr__(card, "conditions", ("",))
    object.__setattr__(card, "effects", ("hospital_dark",))
    object.__setattr__(card, "priority", -1)
    before = (
        card.event_id, card.name, card.event_type, card.participants,
        card.conditions, card.effects, card.priority,
    )

    result = EventCardValidator().validate(card)

    assert not result.valid
    assert any("event_id" in error for error in result.errors)
    assert any("name" in error for error in result.errors)
    assert any("event_type" in error for error in result.errors)
    assert any("participants" in error for error in result.errors)
    assert any("conditions" in error for error in result.errors)
    assert any("priority" in error for error in result.errors)
    assert (
        card.event_id, card.name, card.event_type, card.participants,
        card.conditions, card.effects, card.priority,
    ) == before
