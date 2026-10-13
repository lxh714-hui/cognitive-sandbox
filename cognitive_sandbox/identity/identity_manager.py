from __future__ import annotations

from .character_identity import CharacterIdentity
from .identity_editor import IdentityEditor


class IdentityManager:
    """Own display identities keyed by permanent internal character IDs."""

    def __init__(self, identities=(), *, editor=None):
        self._identities = {}
        self._editor = editor or IdentityEditor()
        values = identities.values() if hasattr(identities, "values") else identities
        for identity in values:
            self.register(identity)

    @property
    def identities(self):
        return tuple(self._identities[key] for key in sorted(self._identities))

    def register(self, identity):
        if not isinstance(identity, CharacterIdentity):
            raise TypeError("identity must be CharacterIdentity.")
        if identity.character_id in self._identities:
            raise ValueError("character identity already registered.")
        self._identities[identity.character_id] = identity
        return identity

    def get(self, character_id):
        return self._identities.get(character_id)

    def display_name_for(self, character_id, fallback=""):
        identity = self.get(character_id)
        return identity.display_name if identity else fallback

    def rename_character(self, character_id, display_name):
        current = self._required(character_id)
        updated = self._editor.rename(current, display_name)
        self._identities[character_id] = updated
        return updated

    def add_alias(self, character_id, alias):
        current = self._required(character_id)
        updated = self._editor.add_alias(current, alias)
        self._identities[character_id] = updated
        return updated

    def update_description(self, character_id, description):
        current = self._required(character_id)
        updated = self._editor.update_description(current, description)
        self._identities[character_id] = updated
        return updated

    def snapshot(self):
        return self.identities

    def _required(self, character_id):
        identity = self.get(character_id)
        if identity is None:
            raise KeyError(character_id)
        return identity

    def restore(self, identities):
        values = tuple(identities)
        if any(not isinstance(item, CharacterIdentity) for item in values):
            raise TypeError("identities must contain CharacterIdentity values.")
        if len({item.character_id for item in values}) != len(values):
            raise ValueError("identity character IDs must be unique.")
        self._identities = {item.character_id: item for item in values}
