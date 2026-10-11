from dataclasses import FrozenInstanceError

import pytest

from cognitive_sandbox.application.director_event_generator import DirectorEventGenerator
from cognitive_sandbox.domain.director_command import DirectorCommand
from cognitive_sandbox.domain.world_events import WorldEvent


def _command(command_type, payload=None):
    return DirectorCommand(
        command_id="command-1",
        command_type=command_type,
        description="导演输入",
        payload=payload if payload is not None else {"weather": "rain", "details": {"intensity": 2}},
    )


@pytest.mark.parametrize(
    ("command_type", "event_type"),
    [
        ("environment_change", "director_environment_change"),
        ("add_pressure", "director_pressure"),
        ("create_event", "director_custom_event"),
    ],
)
def test_supported_command_generates_corresponding_world_event(command_type, event_type):
    event = DirectorEventGenerator(
        world_id="world-1",
        branch_id="branch-1",
        world_revision=4,
        event_id_factory=lambda: "event-1",
    ).generate(_command(command_type))

    assert isinstance(event, WorldEvent)
    assert event.event_type == event_type
    assert event.world_id == "world-1"
    assert event.branch_id == "branch-1"
    assert event.world_revision == 4
    assert event.actor_id == "director"
    assert event.payload["weather"] == "rain"
    assert event.payload["details"]["intensity"] == 2


def test_unknown_command_returns_none():
    assert DirectorEventGenerator().generate(_command("unknown")) is None


def test_command_payload_is_deeply_read_only():
    command = _command("environment_change")

    with pytest.raises(TypeError):
        command.payload["weather"] = "sunny"
    with pytest.raises(TypeError):
        command.payload["details"]["intensity"] = 1
    with pytest.raises(FrozenInstanceError):
        command.command_type = "create_event"


def test_generator_preserves_command_and_source_payload():
    payload = {"weather": "rain", "details": {"intensity": 2}}
    command = _command("add_pressure", payload)
    original = {"weather": "rain", "details": {"intensity": 2}}
    event = DirectorEventGenerator(event_id_factory=lambda: "event-1").generate(command)

    assert payload == original
    assert command.payload == original
    assert event.payload == command.payload
    assert payload["details"]["intensity"] == 2


@pytest.mark.parametrize("field", ["command_id", "command_type", "description"])
def test_command_rejects_empty_required_fields(field):
    values = {
        "command_id": "command-1",
        "command_type": "environment_change",
        "description": "change environment",
        "payload": {},
    }
    values[field] = " "

    with pytest.raises(ValueError, match=field):
        DirectorCommand(**values)
