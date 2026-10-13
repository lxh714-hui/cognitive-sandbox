from __future__ import annotations

from .emotional_state import EmotionalState


class EmotionSpeechAdapter:
    """Translate continuous affect into language-only constraints for a dialogue model."""

    def style_for(self, state: EmotionalState) -> tuple[str, ...]:
        if not isinstance(state, EmotionalState):
            raise TypeError("state must be EmotionalState.")
        styles = []
        if state.anger >= .45:
            styles.append("语气更直接，适度增加质问倾向，避免平静解释。")
        if state.fear >= .55:
            styles.append("表达谨慎和不安，优先确认风险，不要突然变得英勇。")
        if state.sadness >= .5 or state.shame >= .55:
            styles.append("语句收敛，表达低落或迟疑，避免轻佻。")
        if state.hope >= .6:
            styles.append("保留克制的希望感，不保证事情一定成功。")
        if state.curiosity >= .65:
            styles.append("更倾向追问细节，但只询问角色实际知道的内容。")
        if state.calmness >= .7 and state.anger < .35 and state.fear < .35:
            styles.append("保持沉着、清晰的表达。")
        return tuple(styles)

    def emotion_hint(self, state: EmotionalState) -> str:
        if state.anger >= .55:
            return "angry"
        if state.fear >= .6:
            return "afraid"
        if state.sadness >= .55 or state.shame >= .6:
            return "sad"
        if state.hope >= .65 or state.joy >= .65:
            return "hopeful"
        return "calm"
