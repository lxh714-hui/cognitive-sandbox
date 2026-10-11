from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.world_events import WorldEvent


class NarrativeFormatter:
    """Convert supported world events into concise, deterministic narration."""

    _FIXED = {
        "help_attempt": ("一次帮助", "有人伸出了援手"),
        "protect_attempt": ("一次保护", "有人选择保护另一个人"),
        "observe_action": ("开始观察", "角色开始留意周围环境"),
        "director_pressure": ("新的压力", "世界出现了新的压力"),
    }
    _ENVIRONMENT_LABELS = {
        "weather": "天气",
        "danger_level": "危险程度",
        "temperature": "温度",
        "lighting": "光照",
        "location": "地点",
    }

    def format(self, event: WorldEvent) -> NarrativeEvent | None:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        fixed = self._FIXED.get(event.event_type)
        if fixed is not None:
            title, description = fixed
            participants = (event.actor_id,) if event.actor_id != "director" else ()
            return NarrativeEvent(event.event_id, title, description, participants)
        if event.event_type == "director_environment_change":
            return NarrativeEvent(
                source_event_id=event.event_id,
                title="环境发生变化",
                description=self._describe_environment(event.payload),
                participants=(),
            )
        return None

    def _describe_environment(self, payload: Mapping[str, Any]) -> str:
        description = payload.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()

        details = [
            f"{self._ENVIRONMENT_LABELS.get(str(key), str(key))}：{self._render(value)}"
            for key, value in payload.items()
            if key != "description"
        ]
        return "环境发生了变化：" + "，".join(details) if details else "环境发生了变化"

    @staticmethod
    def _render(value: Any) -> str:
        if isinstance(value, Mapping):
            return "、".join(f"{key}={NarrativeFormatter._render(item)}" for key, item in value.items())
        if isinstance(value, (tuple, list)):
            return "、".join(NarrativeFormatter._render(item) for item in value)
        if isinstance(value, (set, frozenset)):
            return "、".join(sorted(NarrativeFormatter._render(item) for item in value))
        return str(value)
