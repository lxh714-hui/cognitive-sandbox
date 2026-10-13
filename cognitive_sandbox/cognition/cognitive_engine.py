from __future__ import annotations

from datetime import datetime, timezone
from types import MappingProxyType

from cognitive_sandbox.cognition.attention_profile import AttentionProfile
from cognitive_sandbox.cognition.belief_inference import Belief, BeliefInference
from cognitive_sandbox.cognition.cognitive_memory import CognitiveMemory
from cognitive_sandbox.cognition.cognitive_rule_provider import CognitiveRuleProvider
from cognitive_sandbox.cognition.cognitive_style import CognitiveStyle, DEFAULT_COGNITIVE_STYLE
from cognitive_sandbox.cognition.reasoning_profile import ReasoningProfile
from cognitive_sandbox.cognition.thought_pattern import ThoughtPattern


class CognitiveEngine:
    """Match scenario-authored interpretation rules against caller-visible information."""

    def __init__(self, styles=None, reasoning_profiles=None, attention_profiles=None,
                 beliefs=None, memories=None, thoughts=None, *, clock=None, rules=()):
        self.styles = dict(styles or {})
        self.reasoning_profiles = dict(reasoning_profiles or {})
        self.attention_profiles = dict(attention_profiles or {})
        self.beliefs = {key: tuple(value) for key, value in (beliefs or {}).items()}
        self.memories = {key: tuple(value) for key, value in (memories or {}).items()}
        self.thoughts = {key: list(value) for key, value in (thoughts or {}).items()}
        self.rule_provider = CognitiveRuleProvider(rules)
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    def style_for(self, character_id):
        return self.styles.get(character_id, DEFAULT_COGNITIVE_STYLE)

    def reasoning_for(self, character_id):
        return self.reasoning_profiles.get(character_id, ReasoningProfile())

    def attention_for(self, character_id):
        return self.attention_profiles.get(character_id, AttentionProfile())

    def attend(self, character_id: str, visible_information) -> tuple[str, ...]:
        """Rank caller-provided visible strings using only matching rule categories."""
        if not isinstance(character_id, str) or not character_id.strip():
            raise ValueError("character_id must not be empty.")
        if isinstance(visible_information, (str, bytes)):
            raise TypeError("visible_information must be a collection of strings.")
        profile = self.attention_for(character_id)
        ranked = []
        for index, item in enumerate(tuple(visible_information)):
            if not isinstance(item, str) or not item.strip():
                continue
            match = self.rule_provider.match(item)
            score = getattr(profile, match.category, 0.5) if match is not None else 0.5
            ranked.append((score, index, item.strip()))
        ranked.sort(key=lambda value: (-value[0], value[1]))
        return tuple(item for _, _, item in ranked)

    def interpret_event(self, character_id: str, world_event, visible_information=()) -> ThoughtPattern:
        event_id = getattr(world_event, "event_id", None)
        if not isinstance(event_id, str) or not event_id:
            raise TypeError("world_event must provide an event_id.")
        focused = self.attend(character_id, visible_information)
        match = next((result for item in focused
                      if (result := self.rule_provider.match(item)) is not None), None)
        if match is None:
            interpretation = "目前提供的信息不足以形成场景解释。"
            confidence = 0.25
            path = ("仅使用调用方提供的可见信息", "没有匹配到场景认知规则")
        else:
            interpretation = match.interpretation
            profile = self.attention_for(character_id)
            # Attention affects confidence only; the scenario owns the meaning.
            attention = getattr(profile, match.category, 0.5)
            confidence = max(0.0, min(1.0, match.confidence + (attention - 0.5) * 0.2))
            path = ("仅使用调用方提供的可见信息", f"匹配场景规则类别：{match.category}")

        thought = ThoughtPattern(character_id, event_id, focused, interpretation,
                                 confidence, path)
        self.thoughts.setdefault(character_id, []).append(thought)
        return thought

    def infer_belief(self, character_id, source_fact, interpretation=None, confidence=None, persistence=.5):
        thought = self.thoughts.get(character_id, ())
        if interpretation is None:
            if not thought:
                raise ValueError("a visible interpretation is required before inferring a belief.")
            interpretation = thought[-1].interpretation
        if confidence is None:
            confidence = thought[-1].confidence if thought else .5
        belief = BeliefInference().infer(character_id, source_fact, interpretation, confidence, persistence)
        self.beliefs[character_id] = (*self.beliefs.get(character_id, ()), belief)
        return belief

    def record_belief_change(self, character_id, source_event, previous, updated):
        if not isinstance(previous, Belief) or not isinstance(updated, Belief):
            raise TypeError("previous and updated must be Belief values.")
        if previous.character_id != character_id or updated.character_id != character_id:
            raise ValueError("beliefs must belong to the character.")
        if previous.interpretation == updated.interpretation:
            return None
        memory = CognitiveMemory(character_id, source_event, previous.interpretation,
                                 updated.interpretation, self._clock())
        self.memories[character_id] = (*self.memories.get(character_id, ()), memory)
        self.beliefs[character_id] = (*tuple(item for item in self.beliefs.get(character_id, ())
                                                if item.source_fact != updated.source_fact), updated)
        return memory

    def context_for(self, character_id):
        thought = self.thoughts.get(character_id, ())
        return MappingProxyType({
            "cognitive_style": self.style_for(character_id),
            "reasoning_profile": self.reasoning_for(character_id),
            "current_interpretation": thought[-1] if thought else None,
            "beliefs": tuple(self.beliefs.get(character_id, ())),
        })
