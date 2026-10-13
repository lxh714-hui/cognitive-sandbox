from dataclasses import dataclass


@dataclass(frozen=True)
class PropagationRule:
    minimum_score: float = 0.45
    distance_penalty: float = 0.25
    relationship_weight: float = 0.25
    agency_weight: float = 0.15
    reliability_weight: float = 0.35
    location_match_bonus: float = 0.25
    reliability_decay: float = 0.12
    distortion_per_hop: float = 0.08

    def __post_init__(self):
        for name in ("minimum_score", "distance_penalty", "relationship_weight", "agency_weight",
                     "reliability_weight", "location_match_bonus", "reliability_decay", "distortion_per_hop"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
            object.__setattr__(self, name, float(value))

    def score(self, *, same_location: bool, trust: float, agency: float, reliability: float, permission: bool) -> float:
        if not permission:
            return 0.0
        trust_signal = max(0.0, min(1.0, (trust + 100.0) / 200.0))
        score = (reliability * self.reliability_weight + trust_signal * self.relationship_weight
                 + max(0.0, min(1.0, agency)) * self.agency_weight
                 + (self.location_match_bonus if same_location else 0.0)
                 - (0.0 if same_location else self.distance_penalty))
        return max(0.0, min(1.0, score))
