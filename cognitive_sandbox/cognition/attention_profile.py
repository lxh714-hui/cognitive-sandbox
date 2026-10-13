from dataclasses import dataclass


@dataclass(frozen=True)
class AttentionProfile:
    physical_detail: float = 0.5
    social_signal: float = 0.5
    emotional_signal: float = 0.5
    risk_signal: float = 0.5
    resource_signal: float = 0.5
    temporal_pattern: float = 0.5

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
