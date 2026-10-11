from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from cognitive_sandbox.domain.character import CharacterState


@dataclass(frozen=True)
class CharacterInitializationRequest:
    prompt: str

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must not be empty.")


class CharacterInitializer:
    """Create static starter character data from a short text description."""

    def __init__(self, *, character_id_factory: Callable[[], str] | None = None) -> None:
        self._character_id_factory = character_id_factory or (lambda: f"character_{uuid4().hex}")

    def initialize(self, request: CharacterInitializationRequest) -> CharacterState:
        if not isinstance(request, CharacterInitializationRequest):
            raise TypeError("request must be a CharacterInitializationRequest.")

        prompt = request.prompt.strip()
        normalized = prompt.casefold()
        if any(keyword in normalized for keyword in ("医生", "doctor", "physician")):
            role = "医生"
            traits = ("谨慎", "富有同情心")
            goals = ("帮助他人",)
            fears = ("无法及时救助他人",)
            memories: tuple[str, ...] = ()
        elif any(keyword in normalized for keyword in ("士兵", "军人", "soldier")):
            role = "士兵"
            traits = ("勇敢", "纪律性")
            goals = ("保护同伴", "完成职责")
            fears = ("失去战友",)
            memories = ()
        else:
            role = "普通居民"
            traits = ("适应力强",)
            goals = ("维持日常生活",)
            fears = ()
            memories = ()

        character_id = self._character_id_factory()
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id_factory must return a non-empty string.")
        return CharacterState(
            character_id=character_id,
            name=prompt,
            role=role,
            traits=traits,
            goals=goals,
            fears=fears,
            memories=memories,
        )
