from __future__ import annotations

from dataclasses import dataclass

from .authority_level import AuthorityLevel


@dataclass(frozen=True)
class CharacterAuthority:
    character_id: str
    authority_level: AuthorityLevel
    controllable: bool
    visible_information_scope: tuple[str, ...]
    can_make_autonomous_decisions: bool

    def __post_init__(self):
        if not isinstance(self.character_id, str) or not self.character_id.strip():
            raise ValueError("character_id must not be empty.")
        if not isinstance(self.authority_level, AuthorityLevel):
            raise TypeError("authority_level must be AuthorityLevel.")
        if not isinstance(self.controllable, bool) or not isinstance(self.can_make_autonomous_decisions, bool):
            raise TypeError("authority flags must be bool values.")
        if isinstance(self.visible_information_scope, (str, bytes)):
            raise TypeError("visible_information_scope must be a collection of strings.")
        scope = tuple(self.visible_information_scope)
        if any(not isinstance(item, str) or not item.strip() for item in scope):
            raise ValueError("visible_information_scope must contain non-empty strings.")
        object.__setattr__(self, "visible_information_scope", scope)
        if self.authority_level is AuthorityLevel.PLAYER:
            if not self.controllable or self.can_make_autonomous_decisions:
                raise ValueError("player authority must be controllable and non-autonomous.")
        elif self.authority_level in {AuthorityLevel.IMPORTANT_CHARACTER, AuthorityLevel.BACKGROUND_CHARACTER}:
            if self.controllable or not self.can_make_autonomous_decisions:
                raise ValueError("NPC authority must be autonomous and not player-controllable.")

    @classmethod
    def player(cls, character_id: str):
        return cls(character_id, AuthorityLevel.PLAYER, True, ("self", "public", "owned_knowledge"), False)

    @classmethod
    def important_character(cls, character_id: str):
        return cls(character_id, AuthorityLevel.IMPORTANT_CHARACTER, False,
                   ("self", "public", "owned_knowledge", "self_emotion", "own_relationships", "visible_goal"), True)

    @classmethod
    def background_character(cls, character_id: str):
        return cls(character_id, AuthorityLevel.BACKGROUND_CHARACTER, False,
                   ("self", "public_limited", "owned_knowledge_limited", "self_emotion", "own_relationships", "visible_goal"), True)

