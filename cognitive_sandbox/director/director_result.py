from __future__ import annotations

from dataclasses import dataclass

from .director_constraint import DirectorConstraint
from .director_intent import DirectorIntent
from .director_path_finder import DirectorPath


@dataclass(frozen=True)
class DirectorResult:
    intent: DirectorIntent
    constraint: DirectorConstraint
    accepted: bool
    explanation: str
    paths: tuple[DirectorPath, ...] = ()
    affected_threads: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.intent, DirectorIntent) or not isinstance(self.constraint, DirectorConstraint):
            raise TypeError("DirectorResult requires an intent and constraint.")
        if not isinstance(self.accepted, bool) or not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("result status and explanation are required.")
        for name in ("paths", "affected_threads"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
