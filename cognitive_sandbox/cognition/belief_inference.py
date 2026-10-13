from dataclasses import dataclass


@dataclass(frozen=True)
class Belief:
    """A character-scoped interpretation of a fact; never a world fact itself."""

    source_fact: str
    interpretation: str
    confidence: float
    persistence: float
    character_id: str = ""

    def __post_init__(self):
        for name in ("source_fact", "interpretation"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty.")
        if not 0 <= self.confidence <= 1 or not 0 <= self.persistence <= 1:
            raise ValueError("confidence and persistence must be between 0 and 1.")


class BeliefInference:
    """Create beliefs only from information explicitly supplied by the caller."""

    def infer(self, character_id: str, source_fact: str, interpretation: str,
              confidence: float = 0.5, persistence: float = 0.5) -> Belief:
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        return Belief(source_fact, interpretation, confidence, persistence, character_id)
