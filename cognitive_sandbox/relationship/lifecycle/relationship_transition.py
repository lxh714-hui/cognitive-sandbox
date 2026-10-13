from dataclasses import dataclass

from .relationship_stage import RelationshipStage


@dataclass(frozen=True)
class RelationshipTransition:
    character_a: str
    character_b: str
    previous_stage: RelationshipStage
    new_stage: RelationshipStage
    source_event_id: str
    reason: str
    timestamp: str = ""

    def __post_init__(self):
        for name in ("character_a", "character_b", "source_event_id", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.character_a == self.character_b:
            raise ValueError("relationship participants must be different.")
        for name in ("previous_stage", "new_stage"):
            value = getattr(self, name)
            if not isinstance(value, RelationshipStage):
                object.__setattr__(self, name, RelationshipStage(value))
        if not isinstance(self.timestamp, str):
            raise TypeError("timestamp must be a string.")


@dataclass(frozen=True)
class RelationshipDynamics:
    character_a: str
    character_b: str
    familiarity: float = 0.0
    dependence: float = 0.0
    distance: float = 1.0
    shared_experience: int = 0

    def __post_init__(self):
        for name in ("character_a", "character_b"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        if self.character_a == self.character_b:
            raise ValueError("relationship participants must be different.")
        for name in ("familiarity", "dependence", "distance"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
            object.__setattr__(self, name, float(value))
        if isinstance(self.shared_experience, bool) or not isinstance(self.shared_experience, int) or self.shared_experience < 0:
            raise ValueError("shared_experience must be a non-negative integer.")
