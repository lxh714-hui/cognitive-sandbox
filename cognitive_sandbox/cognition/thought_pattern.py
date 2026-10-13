from dataclasses import dataclass


@dataclass(frozen=True)
class ThoughtPattern:
    character_id: str
    source_event: str
    observation_focus: tuple[str, ...]
    interpretation: str
    confidence: float
    reasoning_path: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("character_id", "source_event", "interpretation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")
        object.__setattr__(self, "observation_focus", tuple(self.observation_focus))
        object.__setattr__(self, "reasoning_path", tuple(self.reasoning_path))
