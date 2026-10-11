from __future__ import annotations

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.dialogue import DialogueLine


class DialogueGenerator:
    """Generate a small deterministic line from character traits and situation."""

    def generate(
        self,
        speaker: AgentContext,
        target: AgentContext | None,
        situation: str,
    ) -> DialogueLine | None:
        if not isinstance(speaker, AgentContext):
            raise TypeError("speaker must be an AgentContext.")
        if target is not None and not isinstance(target, AgentContext):
            raise TypeError("target must be an AgentContext or None.")
        if not isinstance(situation, str):
            raise TypeError("situation must be a string.")

        traits = {trait.casefold() for trait in speaker.character_state.traits}
        normalized_situation = situation.casefold()
        if "compassionate" in traits and "help" in normalized_situation:
            return DialogueLine(speaker.character_id, "我只是做了应该做的事。", "calm")
        if "brave" in traits and "danger" in normalized_situation:
            return DialogueLine(speaker.character_id, "退后，我来处理。", "determined")
        return None
