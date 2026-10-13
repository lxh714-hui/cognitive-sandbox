from __future__ import annotations

from collections.abc import Mapping

from cognitive_sandbox.application.dialogue_generator import DialogueGenerator
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.character_mind import CharacterMind, KnowledgeContext
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.emotion.emotional_state import EmotionalState
from cognitive_sandbox.emotion.speech_adapter import EmotionSpeechAdapter


class CharacterDialogueService:
    """Generate character dialogue with scoped AI knowledge and rule fallback."""

    def __init__(self, ai_adapter=None, fallback: DialogueGenerator | None = None, emotion_speech_adapter=None) -> None:
        if ai_adapter is not None and not callable(getattr(ai_adapter, "generate_dialogue", None)):
            raise TypeError("ai_adapter must provide generate_dialogue().")
        if fallback is not None and not callable(getattr(fallback, "generate", None)):
            raise TypeError("fallback must provide generate().")
        self._ai_adapter = ai_adapter
        self._fallback = fallback or DialogueGenerator()
        self._emotion_speech = emotion_speech_adapter or EmotionSpeechAdapter()

    def generate(
        self,
        speaker: AgentContext,
        target: AgentContext | None,
        situation: str,
    ) -> DialogueLine | None:
        return self.generate_with_context(speaker, target, situation)

    def generate_with_context(
        self,
        speaker: AgentContext,
        target: AgentContext | None,
        situation: str,
        *,
        character_mind: CharacterMind | None = None,
        knowledge_context: KnowledgeContext | None = None,
        current_event: str | None = None,
        current_scene: Mapping | None = None,
        emotional_state: EmotionalState | None = None,
        authority_context: Mapping | None = None,
        cognitive_context: Mapping | None = None,
    ) -> DialogueLine | None:
        if not isinstance(speaker, AgentContext):
            raise TypeError("speaker must be an AgentContext.")
        if target is not None and not isinstance(target, AgentContext):
            raise TypeError("target must be an AgentContext or None.")
        if not isinstance(situation, str):
            raise TypeError("situation must be a string.")
        if character_mind is not None and not isinstance(character_mind, CharacterMind):
            raise TypeError("character_mind must be a CharacterMind or None.")
        if knowledge_context is not None and not isinstance(knowledge_context, KnowledgeContext):
            raise TypeError("knowledge_context must be a KnowledgeContext or None.")
        if emotional_state is not None and not isinstance(emotional_state, EmotionalState):
            raise TypeError("emotional_state must be EmotionalState or None.")

        if self._ai_adapter is not None:
            scene = dict(current_scene or {})
            scene["situation"] = situation
            if emotional_state is not None:
                style = self._emotion_speech.style_for(emotional_state)
                if style:
                    scene["emotional_style"] = style
            if isinstance(current_event, str) and current_event.strip():
                scene["current_event"] = current_event.strip()
            try:
                kwargs = {
                    "character_mind": character_mind,
                    "knowledge_context": knowledge_context,
                    "current_scene": scene,
                }
                if authority_context is not None:
                    kwargs["authority_context"] = dict(authority_context)
                if cognitive_context is not None:
                    kwargs["cognitive_context"] = _safe_cognitive_context(cognitive_context)
                text = self._ai_adapter.generate_dialogue(speaker, target, situation, **kwargs)
                if isinstance(text, str) and text.strip() and not text.startswith(
                    "LLM provider error:"
                ):
                    return DialogueLine(speaker.character_id, text.strip(), "")
            except Exception:
                # The established deterministic dialogue rules remain the safe fallback.
                pass
        line = self._fallback.generate(speaker, target, situation)
        if line is not None and emotional_state is not None:
            from dataclasses import replace
            line = replace(line, emotion_hint=self._emotion_speech.emotion_hint(emotional_state))
        return line


def _safe_cognitive_context(context):
    if not isinstance(context, Mapping):
        raise TypeError("cognitive_context must be a mapping.")
    style = context.get("cognitive_style")
    reasoning = context.get("reasoning_profile")
    thought = context.get("current_interpretation")
    return {
        "cognitive_style": ({name: getattr(style, name) for name in style.__dataclass_fields__}
                            if style is not None else {}),
        "reasoning_profile": ({name: getattr(reasoning, name) for name in reasoning.__dataclass_fields__}
                              if reasoning is not None else {}),
        "current_interpretation": getattr(thought, "interpretation", "") if thought is not None else "",
        "observation_focus": tuple(getattr(thought, "observation_focus", ())) if thought is not None else (),
    }
