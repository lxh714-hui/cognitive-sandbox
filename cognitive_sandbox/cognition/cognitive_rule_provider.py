from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CognitiveRuleMatch:
    pattern: str
    category: str
    interpretation: str
    confidence: float
    priority: int = 0


class CognitiveRuleProvider:
    """Validates and matches scenario-authored interpretation rules.

    Patterns are literal substrings. This deliberately supports no scripting,
    callbacks, or world semantics in the engine.
    """

    def __init__(self, rules=()):
        if isinstance(rules, (str, bytes)) or not isinstance(rules, (tuple, list)):
            raise TypeError("cognitive rules must be a sequence of mappings.")
        normalized = []
        for index, rule in enumerate(rules):
            normalized.append(self._normalize(rule, index))
        self.rules = tuple(normalized)

    @classmethod
    def validate(cls, rules):
        try:
            cls(rules)
        except (TypeError, ValueError) as error:
            return (str(error),)
        return ()

    def match(self, text: str) -> CognitiveRuleMatch | None:
        if not isinstance(text, str):
            return None
        folded = text.casefold()
        matches = [rule for rule in self.rules if rule.pattern.casefold() in folded]
        if not matches:
            return None
        return max(matches, key=lambda rule: (rule.priority, len(rule.pattern)))

    @staticmethod
    def _normalize(rule, index):
        label = f"cognitive_rules[{index}]"
        if not isinstance(rule, Mapping):
            raise TypeError(f"{label} must be an object.")
        pattern = rule.get("pattern")
        category = rule.get("category")
        interpretation = rule.get("interpretation")
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError(f"{label}.pattern must not be empty.")
        if not isinstance(category, str) or not category.strip():
            raise ValueError(f"{label}.category must not be empty.")
        if not isinstance(interpretation, str) or not interpretation.strip():
            raise ValueError(f"{label}.interpretation must not be empty.")
        confidence = rule.get("confidence", 0.5)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError(f"{label}.confidence must be between 0 and 1.")
        priority = rule.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise ValueError(f"{label}.priority must be an integer.")
        return CognitiveRuleMatch(pattern.strip(), category.strip(), interpretation.strip(),
                                  float(confidence), priority)
