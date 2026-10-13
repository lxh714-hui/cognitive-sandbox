from cognitive_sandbox.character_presence import CharacterPresence, EntryRule, PresenceManager, PresenceState
from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.application.player_action_parser import PlayerActionParser


def test_character_card_registration_does_not_introduce_character():
    manager = PresenceManager()
    manager.register_character("liuyi")
    manager.add_rule(EntryRule("liuyi", trigger_event_types=("anomaly_found",), allowed_locations=("station",)))
    assert manager.get("liuyi").availability is PresenceState.UNKNOWN
    assert manager.evaluate_entry("liuyi", event_type="ordinary_event", current_location="station").availability is PresenceState.UNKNOWN
    assert manager.evaluate_entry("liuyi", event_type="anomaly_found", current_location="station").availability is PresenceState.AVAILABLE
    assert manager.introduce("liuyi", current_location="station").introduction_state is PresenceState.INTRODUCED


def test_presence_does_not_allow_entry_from_wrong_location():
    manager = PresenceManager(entry_rules=(EntryRule("liuyi", ("anomaly_found",), allowed_locations=("station",)),))
    assert manager.evaluate_entry("liuyi", event_type="anomaly_found", current_location="market").availability is PresenceState.UNKNOWN


def test_presence_model_is_immutable_and_normalizes_conditions():
    presence = CharacterPresence("x", entry_conditions=["goal"])
    assert presence.entry_conditions == ("goal",)
    try:
        presence.current_location = "elsewhere"
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("presence must be immutable")


def test_location_change_requires_travel_and_left_character_can_reenter_only_by_rule():
    manager = PresenceManager(entry_rules=(EntryRule("x", trigger_event_types=("arrived",)),))
    manager.evaluate_entry("x", event_type="arrived", current_location="north")
    manager.introduce("x")
    manager.activate("x")
    try:
        manager.move_to("x", "south")
    except ValueError:
        pass
    else:
        raise AssertionError("location changes must preserve causal travel")
    assert manager.move_to("x", "south", travel_completed=True).current_location == "south"
    assert manager.leave("x").availability is PresenceState.LEFT
    assert manager.evaluate_entry("x", event_type="ordinary").availability is PresenceState.LEFT


def test_scenario_character_cards_start_as_unknown_npc_presence():
    session = GameLauncher(action_interpreter=PlayerActionParser()).start_scenario("example_world")
    npc_presence = tuple(item for item in session.presence_manager.presences if item.character_id != session.player_id)
    assert npc_presence
    assert all(item.availability is PresenceState.UNKNOWN for item in npc_presence)
    assert session.presence_manager.get(session.player_id).availability is PresenceState.ACTIVE
