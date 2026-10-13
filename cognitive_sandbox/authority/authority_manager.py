from __future__ import annotations

from types import MappingProxyType

from .authority_error import AuthorityError
from .authority_level import AuthorityLevel
from .character_authority import CharacterAuthority


class AuthorityManager:
    """World-local character permissions and scoped visibility checks."""

    DIRECTOR_ALLOWED = frozenset({"create_constraint", "view_public_narrative", "propose_direction"})
    DIRECTOR_FORBIDDEN = frozenset({"control_character", "force_action", "view_hidden_knowledge", "view_hidden_motivation", "view_true_emotion"})

    def __init__(self, authorities=(), *, player_character_id: str | None = None):
        self.player_character_id = player_character_id
        self._authorities: dict[str, CharacterAuthority] = {}
        for authority in authorities:
            self.register(authority)
        player_ids = [key for key, value in self._authorities.items() if value.authority_level is AuthorityLevel.PLAYER]
        if len(player_ids) > 1:
            raise AuthorityError("a world may have only one Player Character.")
        if player_ids and player_character_id is not None and player_ids[0] != player_character_id:
            raise AuthorityError("player authority does not match player_character_id.")
        if player_ids:
            self.player_character_id = player_ids[0]
        elif player_character_id:
            self.register(CharacterAuthority.player(player_character_id))

    @property
    def authorities(self):
        return MappingProxyType(self._authorities.copy())

    def register(self, authority: CharacterAuthority) -> None:
        if not isinstance(authority, CharacterAuthority):
            raise TypeError("authority must be CharacterAuthority.")
        existing = self._authorities.get(authority.character_id)
        if existing is not None and existing != authority:
            raise AuthorityError(f"authority already exists for character: {authority.character_id}")
        if authority.authority_level is AuthorityLevel.PLAYER:
            current = next((item.character_id for item in self._authorities.values()
                            if item.authority_level is AuthorityLevel.PLAYER), None)
            if current is not None and current != authority.character_id:
                raise AuthorityError("a world may have only one Player Character.")
            if self.player_character_id and self.player_character_id != authority.character_id:
                raise AuthorityError("player_character_id cannot be switched.")
            self.player_character_id = authority.character_id
        self._authorities[authority.character_id] = authority

    def authority_for(self, character_id: str) -> CharacterAuthority | None:
        return self._authorities.get(character_id)

    def check_control_permission(self, character_id: str, *, requester_id: str | None = None,
                                 requester_level: AuthorityLevel = AuthorityLevel.PLAYER) -> bool:
        authority = self.authority_for(character_id)
        if authority is None or requester_level is not AuthorityLevel.PLAYER:
            return False
        requester_id = requester_id or self.player_character_id
        return bool(authority.controllable and character_id == self.player_character_id == requester_id)

    def require_control_permission(self, character_id: str, *, requester_id: str | None = None,
                                   requester_level: AuthorityLevel = AuthorityLevel.PLAYER) -> CharacterAuthority:
        authority = self.authority_for(character_id)
        if authority is None:
            raise AuthorityError(f"unknown character authority: {character_id}")
        if self.check_control_permission(character_id, requester_id=requester_id, requester_level=requester_level):
            return authority
        if authority.authority_level is AuthorityLevel.IMPORTANT_CHARACTER:
            raise AuthorityError("Important character is autonomous and cannot be possessed.")
        raise AuthorityError("character control is not permitted.")

    def check_autonomous_permission(self, character_id: str) -> bool:
        authority = self.authority_for(character_id)
        return bool(authority and authority.can_make_autonomous_decisions and not authority.controllable)

    def require_autonomous_permission(self, character_id: str) -> CharacterAuthority:
        authority = self.authority_for(character_id)
        if not self.check_autonomous_permission(character_id):
            raise AuthorityError(f"autonomous action is not permitted for character: {character_id}")
        return authority

    def check_visibility_permission(self, viewer_id: str, character_id: str,
                                    information_scope: str = "public", *,
                                    requester_level: AuthorityLevel = AuthorityLevel.PLAYER) -> bool:
        authority = self.authority_for(character_id)
        if authority is None or not isinstance(information_scope, str):
            return False
        if requester_level is AuthorityLevel.DEBUG:
            return True
        if requester_level is AuthorityLevel.DIRECTOR and information_scope not in {
            "public", "public_status", "public_narrative"
        }:
            return False
        if viewer_id == character_id and "self" in authority.visible_information_scope:
            return information_scope not in {"hidden_world", "other_character_hidden"}
        if information_scope in {"hidden", "hidden_world", "hidden_knowledge", "hidden_motivation", "true_emotion", "private_relationship"}:
            return False
        if information_scope == "own_relationships":
            return viewer_id == self.player_character_id or viewer_id == character_id
        if information_scope == "public_limited":
            return "public_limited" in authority.visible_information_scope
        return information_scope in {"public", "public_status", "public_narrative"}

    def check_director_permission(self, operation: str, *, requester_level: AuthorityLevel = AuthorityLevel.DIRECTOR) -> bool:
        if not isinstance(operation, str):
            return False
        if requester_level is not AuthorityLevel.DIRECTOR:
            return False
        if operation in self.DIRECTOR_FORBIDDEN:
            return False
        return operation in self.DIRECTOR_ALLOWED

    def require_director_permission(self, operation: str, *, requester_level: AuthorityLevel = AuthorityLevel.DIRECTOR) -> None:
        if not self.check_director_permission(operation, requester_level=requester_level):
            raise AuthorityError(f"director operation is not permitted: {operation}")

    def switch_player_character(self, character_id: str) -> None:
        if character_id != self.player_character_id:
            self.require_control_permission(character_id, requester_id=self.player_character_id)

    def ai_authority_context(self, character_id: str) -> dict:
        authority = self.authority_for(character_id)
        if authority is None:
            raise AuthorityError(f"unknown character authority: {character_id}")
        return {
            "character_id": character_id,
            "authority_level": authority.authority_level.name,
            "allowed_information": authority.visible_information_scope,
            "excluded_information": (
                "complete_world_state", "other_character_hidden_knowledge", "hidden_motivation",
                "other_character_emotion", "all_relationships",
            ),
        }

