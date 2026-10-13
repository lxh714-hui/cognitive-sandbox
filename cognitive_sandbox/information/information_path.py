from dataclasses import dataclass


@dataclass(frozen=True)
class InformationPath:
    clue_id: str
    holders: tuple[str, ...]
    reliability: float
    timestamp: str
    source_types: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.clue_id or not self.clue_id.strip():
            raise ValueError("clue_id must not be empty")
        holders = tuple(self.holders)
        sources = tuple(self.source_types)
        if not holders or any(not isinstance(item, str) or not item.strip() for item in holders):
            raise ValueError("holders must contain non-empty IDs")
        if not 0 <= self.reliability <= 1:
            raise ValueError("reliability must be between 0 and 1")
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("timestamp must not be empty")
        object.__setattr__(self, "holders", holders)
        object.__setattr__(self, "source_types", sources)
