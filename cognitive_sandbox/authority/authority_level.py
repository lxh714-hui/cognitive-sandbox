from __future__ import annotations

from enum import IntEnum


class AuthorityLevel(IntEnum):
    BACKGROUND_CHARACTER = 10
    IMPORTANT_CHARACTER = 20
    PLAYER = 30
    DIRECTOR = 40
    DEBUG = 50

