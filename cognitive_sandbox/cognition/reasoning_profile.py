from dataclasses import dataclass


@dataclass(frozen=True)
class ReasoningProfile:
    reasoning_depth: float = 0.5
    reflection_tendency: float = 0.5
    causal_search: float = 0.5
    future_prediction: float = 0.5

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
