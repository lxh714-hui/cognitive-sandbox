from __future__ import annotations

from .character_motivation import CharacterMotivation


class MotivationManager:
    """Stores layered motives and exposes only viewer-authorized projections."""

    def __init__(self, motivations=()):
        self._motivations = {}
        for motivation in motivations:
            self.set(motivation)

    @property
    def motivations(self):
        return tuple(self._motivations[key] for key in sorted(self._motivations))

    def set(self, motivation):
        if not isinstance(motivation, CharacterMotivation):
            raise TypeError("motivation must be CharacterMotivation.")
        self._motivations[motivation.character_id] = motivation
        return motivation

    def get(self, character_id):
        return self._motivations.get(character_id)

    def get_for_character(self, character_id, viewer_id=None, *, privileged=False):
        motivation = self.get(character_id)
        if motivation is None:
            return None
        # Default callers get the public layer only. Debug tools must explicitly request privilege.
        return motivation.view_for(viewer_id or "", privileged=privileged)
