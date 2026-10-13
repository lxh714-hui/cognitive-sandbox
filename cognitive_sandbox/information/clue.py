from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Clue:
    clue_id: str
    source_event: str
    content_type: str
    reliability: float
    visibility: str = "public"
    location: str | None = None
    created_time: str = "unknown"
    content: str = ""
    related_entities: tuple[str, ...] = ()

    def __post_init__(self):
        for field in ("clue_id", "source_event", "content_type", "visibility", "created_time"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must not be empty")
        if self.location is not None and (not isinstance(self.location, str) or not self.location.strip()):
            raise ValueError("location must be non-empty or None")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if isinstance(self.reliability, bool) or not isinstance(self.reliability, (int, float)) or not math.isfinite(self.reliability) or not 0 <= self.reliability <= 1:
            raise ValueError("reliability must be between 0 and 1")
        object.__setattr__(self, "reliability", float(self.reliability))
        entities = tuple(self.related_entities)
        if any(not isinstance(item, str) or not item.strip() for item in entities):
            raise ValueError("related_entities must contain non-empty strings")
        object.__setattr__(self, "related_entities", entities)
