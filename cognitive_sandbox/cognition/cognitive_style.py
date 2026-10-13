from dataclasses import dataclass


@dataclass(frozen=True)
class CognitiveStyle:
    """Default ways a character tends to interpret information, not an ability score."""

    analytical: float = 0.5
    intuitive: float = 0.5
    creative: float = 0.5
    suspicious: float = 0.5
    pragmatic: float = 0.5
    emotional: float = 0.5
    strategic: float = 0.5

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")


DEFAULT_COGNITIVE_STYLE = CognitiveStyle()
