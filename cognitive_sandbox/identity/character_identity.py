from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterIdentity:
    character_id: str
    display_name: str
    original_name: str
    aliases: tuple[str, ...] = ()
    editable: bool = True
    naming_source: str = "user"
    public_description: str = ""

    def __post_init__(self):
        for name in ("character_id", "display_name", "original_name", "naming_source"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        aliases = tuple(self.aliases)
        if any(not isinstance(item, str) or not item.strip() for item in aliases):
            raise ValueError("aliases must contain non-empty strings.")
        object.__setattr__(self, "aliases", tuple(dict.fromkeys(aliases)))
        if not isinstance(self.editable, bool):
            raise TypeError("editable must be a boolean.")
        if not isinstance(self.public_description, str):
            raise TypeError("public_description must be a string.")
