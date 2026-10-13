from dataclasses import dataclass


@dataclass(frozen=True)
class CognitiveMemory:
    character_id: str
    source_event: str
    previous_interpretation: str
    new_interpretation: str
    created_at: str

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
