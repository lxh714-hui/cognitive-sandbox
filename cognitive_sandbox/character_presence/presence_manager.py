from __future__ import annotations

from dataclasses import replace

from .character_presence import CharacterPresence, PresenceState
from .entry_rule import EntryRule


class PresenceManager:
    """Tracks story availability independently from character-card registration."""

    def __init__(self, presences=(), entry_rules=()):
        self._presences = {}
        self._rules = {}
        for presence in presences:
            self.restore_presence(presence)
        for rule in entry_rules:
            self.add_rule(rule)

    @property
    def presences(self):
        return tuple(self._presences[key] for key in sorted(self._presences))

    @property
    def entry_rules(self):
        return tuple(self._rules[key] for key in sorted(self._rules))

    def register_character(self, character_id, *, current_location=None, entry_conditions=()):
        if character_id in self._presences:
            return self._presences[character_id]
        presence = CharacterPresence(character_id, current_location, PresenceState.UNKNOWN, PresenceState.UNKNOWN, tuple(entry_conditions))
        self._presences[character_id] = presence
        return presence

    def add_rule(self, rule):
        if not isinstance(rule, EntryRule):
            raise TypeError("rule must be EntryRule.")
        if rule.character_id in self._rules:
            raise ValueError("each character can have one entry rule.")
        self._rules[rule.character_id] = rule
        self._presences.setdefault(rule.character_id, CharacterPresence(rule.character_id))
        return rule

    def get(self, character_id):
        return self._presences.get(character_id)

    def evaluate_entry(self, character_id, *, event_type=None, active_goal_types=(), current_location=None, current_time=None):
        active_goal_types = tuple(active_goal_types)
        presence = self._presences.get(character_id) or self.register_character(character_id)
        if presence.availability not in {PresenceState.UNKNOWN, PresenceState.LEFT}:
            return presence
        rule = self._rules.get(character_id)
        if rule is None or not rule.matches(event_type=event_type, active_goal_types=active_goal_types,
                                            current_location=current_location, current_time=current_time):
            return presence
        matched = []
        if event_type and event_type in rule.trigger_event_types:
            matched.append(f"event:{event_type}")
        matched.extend(f"goal:{goal}" for goal in rule.required_goal_types if goal in active_goal_types)
        if current_location:
            matched.append(f"location:{current_location}")
        if current_time:
            matched.append(f"time:{current_time}")
        updated = replace(presence, current_location=current_location, availability=PresenceState.AVAILABLE,
                          entry_conditions=tuple(matched))
        self._presences[character_id] = updated
        return updated

    def introduce(self, character_id, *, current_location=None):
        presence = self._presences.get(character_id)
        if presence is None or presence.availability is not PresenceState.AVAILABLE:
            raise ValueError("character is not available for introduction.")
        rule = self._rules.get(character_id)
        if rule and rule.allowed_locations and current_location not in rule.allowed_locations:
            raise ValueError("character cannot be introduced at this location.")
        if current_location is None:
            current_location = presence.current_location
        updated = replace(presence, current_location=current_location,
                          availability=PresenceState.INTRODUCED, introduction_state=PresenceState.INTRODUCED)
        self._presences[character_id] = updated
        return updated

    def activate(self, character_id):
        presence = self._presences[character_id]
        if presence.introduction_state not in {PresenceState.INTRODUCED, PresenceState.ACTIVE}:
            raise ValueError("character must be introduced before activation.")
        updated = replace(presence, availability=PresenceState.ACTIVE, introduction_state=PresenceState.ACTIVE)
        self._presences[character_id] = updated
        return updated

    def move_to(self, character_id, location, *, travel_completed=False):
        presence = self._presences[character_id]
        if presence.introduction_state not in {PresenceState.INTRODUCED, PresenceState.ACTIVE}:
            raise ValueError("character must be introduced before changing location.")
        if not isinstance(location, str) or not location.strip():
            raise ValueError("location must not be empty.")
        if presence.current_location != location and not travel_completed:
            raise ValueError("location changes require a completed travel transition.")
        updated = replace(presence, current_location=location)
        self._presences[character_id] = updated
        return updated

    def leave(self, character_id):
        presence = self._presences[character_id]
        updated = replace(presence, availability=PresenceState.LEFT, introduction_state=PresenceState.LEFT)
        self._presences[character_id] = updated
        return updated

    def restore_presence(self, presence):
        if not isinstance(presence, CharacterPresence):
            raise TypeError("presence must be CharacterPresence.")
        if presence.character_id in self._presences:
            raise ValueError("duplicate character presence.")
        self._presences[presence.character_id] = presence
        return presence
