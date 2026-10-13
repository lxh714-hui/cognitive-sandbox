from dataclasses import dataclass


@dataclass(frozen=True)
class ConstraintExplanation:
    constraint_id: str
    effect: str
    reason: str
    affected_candidates: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("constraint_id", "effect", "reason"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be empty.")
        object.__setattr__(self, "affected_candidates", tuple(self.affected_candidates))
