from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PatchValidationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PatchValidationResult:
    status: PatchValidationStatus
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, PatchValidationStatus):
            raise TypeError("status must be a PatchValidationStatus.")
        reasons = tuple(self.reasons)
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise ValueError("reasons must contain non-empty strings.")
        object.__setattr__(self, "reasons", reasons)
