from __future__ import annotations

import json
from typing import Protocol

from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.world_events import WorldEvent


class AIGMProvider(Protocol):
    def complete(self, request: AIGMRequest) -> AIGMResponse: ...


class MockAIProvider:
    """Deterministic stand-in for a future hosted or local language model."""

    def complete(self, request: AIGMRequest) -> AIGMResponse:
        if not isinstance(request, AIGMRequest):
            raise TypeError("request must be an AIGMRequest.")
        if request.request_type == "parse_player_action":
            return AIGMResponse(self._parse_action(request.context["player_text"]))
        if request.request_type == "generate_narrative":
            return AIGMResponse(self._narrative(request.context["event"]))
        if request.request_type == "generate_dialogue":
            return AIGMResponse(self._dialogue(request.context["speaker"], request.context["situation"]))
        raise ValueError(f"Unsupported AI GM request type: {request.request_type}")

    @staticmethod
    def _parse_action(player_text: str) -> str:
        if any(word in player_text for word in ("观察", "看看", "查看")):
            intent = "observe"
        elif any(word in player_text for word in ("帮助", "救")):
            intent = "help"
        elif any(word in player_text for word in ("保护", "守护")):
            intent = "protect"
        else:
            return json.dumps({"intent": None, "target": None}, ensure_ascii=False)
        target = "doctor" if "医生" in player_text else "soldier" if "士兵" in player_text else None
        return json.dumps({"intent": intent, "target": target}, ensure_ascii=False)

    @staticmethod
    def _narrative(event: WorldEvent) -> str:
        fixed = {
            "help_attempt": "有人伸出了援手",
            "protect_attempt": "有人选择保护另一个人",
            "director_pressure": "世界出现了新的压力",
        }
        if event.event_type in fixed:
            return fixed[event.event_type]
        if event.event_type == "director_environment_change":
            description = event.payload.get("description")
            if isinstance(description, str) and description.strip():
                return description
            if event.payload:
                return "环境发生变化：" + "，".join(
                    f"{key}：{value}" for key, value in event.payload.items()
                )
            return "环境发生了变化"
        return f"世界发生了变化：{event.event_type}"

    @staticmethod
    def _dialogue(speaker: AgentContext, situation: str) -> str:
        traits = {trait.casefold() for trait in speaker.character_state.traits}
        if "compassionate" in traits and "help" in situation.casefold():
            return "我只是做了应该做的事。"
        if "brave" in traits and "danger" in situation.casefold():
            return "退后，我来处理。"
        return "……"


class AIGMAdapter:
    """Translate application inputs to provider requests and expose text/results."""

    def __init__(self, provider: AIGMProvider | None = None) -> None:
        self._provider = provider or MockAIProvider()

    def parse_player_action(self, player_text: str, context: AgentContext | dict) -> PlayerAction | None:
        if not isinstance(player_text, str) or not player_text.strip():
            raise ValueError("player_text must not be empty.")
        player_id = self._player_id(context)
        response = self._call(
            AIGMRequest(
                "parse_player_action",
                {"player_text": player_text, "player_id": player_id, "agent_context": context},
            )
        )
        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError as error:
            raise ValueError("provider returned invalid structured action JSON.") from error
        if not isinstance(parsed, dict):
            raise ValueError("provider action result must be a JSON object.")
        intent = parsed.get("intent")
        if intent is None:
            return None
        target = parsed.get("target")
        return PlayerAction(player_id, player_text, intent, target)

    def generate_narrative(self, event: WorldEvent, agent_context: AgentContext) -> str:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        if not isinstance(agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        return self._call(
            AIGMRequest("generate_narrative", {"event": event, "agent_context": agent_context})
        ).content

    def generate_dialogue(
        self,
        speaker_context: AgentContext,
        target_context: AgentContext | None,
        situation: str,
    ) -> str:
        if not isinstance(speaker_context, AgentContext):
            raise TypeError("speaker_context must be an AgentContext.")
        if target_context is not None and not isinstance(target_context, AgentContext):
            raise TypeError("target_context must be an AgentContext or None.")
        if not isinstance(situation, str) or not situation.strip():
            raise ValueError("situation must not be empty.")
        return self._call(
            AIGMRequest(
                "generate_dialogue",
                {
                    "speaker": speaker_context,
                    "target": target_context,
                    "situation": situation,
                },
            )
        ).content

    def _call(self, request: AIGMRequest) -> AIGMResponse:
        response = self._provider.complete(request)
        if not isinstance(response, AIGMResponse):
            raise TypeError("AI GM provider must return an AIGMResponse.")
        return response

    @staticmethod
    def _player_id(context: AgentContext | dict) -> str:
        if isinstance(context, AgentContext):
            return context.character_id
        if isinstance(context, dict):
            player_id = context.get("player_id")
            if isinstance(player_id, str) and player_id.strip():
                return player_id
        raise ValueError("context must provide a valid player_id.")
