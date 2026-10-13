from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MessageType(str, Enum):
    PLAYER = "player"
    CHARACTER = "character"
    NARRATION = "narration"
    SYSTEM_TEMP = "system_temp"
    SYSTEM_ERROR = "system_error"
    # Read compatibility for older saved transcripts and callers.
    SYSTEM = "system"


@dataclass(frozen=True)
class DisplayMessage:
    """Immutable presentation record for one item in the visible transcript."""

    message_type: MessageType | str
    content: str
    speaker_id: str | None = None

    def __post_init__(self) -> None:
        try:
            message_type = MessageType(self.message_type)
        except ValueError as error:
            raise ValueError("unsupported message_type.") from error
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("content must not be empty.")
        if self.speaker_id is not None and (
            not isinstance(self.speaker_id, str) or not self.speaker_id.strip()
        ):
            raise ValueError("speaker_id must be None or a non-empty string.")
        object.__setattr__(self, "message_type", message_type)
        object.__setattr__(self, "content", self.content.strip())
