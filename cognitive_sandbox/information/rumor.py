from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Rumor:
    rumor_id: str
    origin_clue: str
    current_holder: str
    reliability: float
    distortion_level: float
    spread_count: int
    content: str = ""
    source_holder: str | None = None

    def __post_init__(self):
        for field in ("rumor_id", "origin_clue", "current_holder"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must not be empty")
        for field in ("reliability", "distortion_level"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{field} must be between 0 and 1")
            object.__setattr__(self, field, float(value))
        if isinstance(self.spread_count, bool) or not isinstance(self.spread_count, int) or self.spread_count < 0:
            raise ValueError("spread_count must be non-negative")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if self.source_holder is not None and (not isinstance(self.source_holder, str) or not self.source_holder.strip()):
            raise ValueError("source_holder must be non-empty or None")
