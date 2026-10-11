from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DialogueLine:
    speaker_id: str
    text: str
    emotion_hint: str = ""

    def __post_init__(self) -> None:
        for name in ("speaker_id", "text"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not isinstance(self.emotion_hint, str):
            raise TypeError("emotion_hint must be a string.")
