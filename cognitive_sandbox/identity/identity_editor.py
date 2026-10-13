from __future__ import annotations

from dataclasses import replace

from .character_identity import CharacterIdentity


class IdentityEditor:
    def rename(self, identity: CharacterIdentity, display_name: str) -> CharacterIdentity:
        _editable(identity)
        _nonempty(display_name, "display_name")
        display_name = display_name.strip()
        if display_name == identity.display_name:
            return identity
        aliases = tuple(dict.fromkeys((*identity.aliases, identity.display_name)))
        return replace(identity, display_name=display_name, aliases=aliases)

    def add_alias(self, identity: CharacterIdentity, alias: str) -> CharacterIdentity:
        _editable(identity)
        _nonempty(alias, "alias")
        return replace(identity, aliases=tuple(dict.fromkeys((*identity.aliases, alias.strip()))))

    def update_description(self, identity: CharacterIdentity, description: str) -> CharacterIdentity:
        _editable(identity)
        if not isinstance(description, str):
            raise TypeError("description must be a string.")
        return replace(identity, public_description=description.strip())


def _editable(identity):
    if not isinstance(identity, CharacterIdentity):
        raise TypeError("identity must be CharacterIdentity.")
    if not identity.editable:
        raise PermissionError("this world package does not allow identity edits for the character.")


def _nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty.")
