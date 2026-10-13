from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Protocol

from cognitive_sandbox.application.ai_context_builder import AIContextBuilder
from cognitive_sandbox.domain.agent_context import AgentContext
from cognitive_sandbox.domain.ai_gm import AIGMRequest, AIGMResponse
from cognitive_sandbox.domain.action_intent import ActionIntent
from cognitive_sandbox.domain.character_mind import (
    CharacterMind,
    Identity,
    KnowledgeContext,
    MemoryContext,
    PersonalityProfile,
    SpeechStyle,
)
from cognitive_sandbox.domain.dialogue import DialogueLine
from cognitive_sandbox.domain.narrative_event import NarrativeEvent
from cognitive_sandbox.domain.player_action import PlayerAction
from cognitive_sandbox.domain.world_events import WorldEvent


class AIGMProvider(Protocol):
    def complete(self, request: AIGMRequest) -> AIGMResponse: ...


class ActionResponseParseError(ValueError):
    """A safe parse failure that keeps the model response for diagnostics."""

    def __init__(self, raw_response: str, reason: str) -> None:
        super().__init__(reason)
        self.raw_response = raw_response
        self.reason = reason


class MockAIProvider:
    """Deterministic stand-in for a future hosted or local language model."""

    def complete(self, request: AIGMRequest) -> AIGMResponse:
        if not isinstance(request, AIGMRequest):
            raise TypeError("request must be an AIGMRequest.")
        if request.request_type == "parse_player_action":
            return AIGMResponse(self._parse_action(request.context["player_text"]))
        if request.request_type == "parse_action_intent":
            from cognitive_sandbox.application.action_intent_parser import ActionIntentParser

            action = ActionIntentParser().parse(
                request.context["actor_id"], request.context["player_text"]
            )
            if action is None:
                return AIGMResponse(json.dumps({"intent": None}, ensure_ascii=False))
            return AIGMResponse(json.dumps({
                "intent": action.intent,
                "target": action.target,
                "object": action.object,
                "parameters": dict(action.parameters),
            }, ensure_ascii=False))
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
    def _dialogue(speaker: Mapping, situation: str) -> str:
        personality = speaker.get("personality", {})
        traits = {trait.casefold() for trait in personality.get("traits", ())}
        if "compassionate" in traits and "help" in situation.casefold():
            return "我只是做了应该做的事。"
        if "brave" in traits and "danger" in situation.casefold():
            return "退后，我来处理。"
        return "……"


class AIGMAdapter:
    """Translate application inputs to provider requests and expose text/results."""

    def __init__(self, provider: AIGMProvider | None = None, *, knowledge_retriever=None) -> None:
        self._provider = provider or MockAIProvider()
        self._context_builder = AIContextBuilder(knowledge_retriever)

    def parse_player_action(self, player_text: str, context: AgentContext | dict) -> PlayerAction | None:
        if not isinstance(player_text, str) or not player_text.strip():
            raise ValueError("player_text must not be empty.")
        player_id = self._player_id(context)
        response = self._call(
            AIGMRequest(
                "parse_player_action",
                {
                    "player_text": player_text,
                    "player_id": player_id,
                    "agent_context": context,
                    "authority_context": _authority_from_context(context, player_id),
                },
            )
        )
        raw_response = response.content
        parsed, extraction_reason = _extract_json_object(raw_response)

        if parsed is not None:
            action_keys = ("action_type", "intent", "action")
            if not any(key in parsed for key in action_keys):
                raise ActionResponseParseError(
                    raw_response, "JSON object is missing action_type or intent."
                )
            raw_intent = _first_present(parsed, "action_type", "intent", "action")
            if raw_intent is None:
                return None
            if not isinstance(raw_intent, str):
                raise ActionResponseParseError(
                    raw_response, "action_type or intent must be a string."
                )
            if not raw_intent.strip():
                return None

            intent = _normalise_action_label(raw_intent)
            if intent is None:
                raise ActionResponseParseError(
                    raw_response, f"unsupported action label: {raw_intent!r}."
                )

            target = parsed.get("target")
            if target is not None and not isinstance(target, str):
                raise ActionResponseParseError(raw_response, "target must be a string or null.")
            target = (
                _normalise_target(target)
                if target is not None
                else _infer_target(raw_response) or _infer_target(player_text)
            )
            if target is not None and not target.strip():
                raise ActionResponseParseError(raw_response, "target must not be empty.")
            return PlayerAction(player_id, player_text, intent, target)

        # Recover a single known label from legacy prose-only model output,
        # such as "开始观察\\n...\\ndoctor". Ambiguous prose is rejected.
        intent = _infer_action_from_text(raw_response)
        if intent is not None:
            return PlayerAction(
                player_id,
                player_text,
                intent,
                _infer_target(raw_response) or _infer_target(player_text),
            )
        raise ActionResponseParseError(raw_response, extraction_reason)

    def parse_action_intent(self, player_text: str, context: AgentContext | dict) -> ActionIntent | None:
        """Parse open-vocabulary intent data without deciding whether it can execute."""
        if not isinstance(player_text, str) or not player_text.strip():
            raise ValueError("player_text must not be empty.")
        actor_id = self._player_id(context)
        response = self._call(
            AIGMRequest(
                "parse_action_intent",
                {
                    "player_text": player_text,
                    "actor_id": actor_id,
                    "authority_context": _authority_from_context(context, actor_id),
                },
            )
        )
        raw_response = response.content
        parsed, extraction_reason = _extract_json_object(raw_response)
        if parsed is None:
            raise ActionResponseParseError(raw_response, extraction_reason)
        raw_intent = _first_present(parsed, "intent", "action_type", "action")
        if not isinstance(raw_intent, str) or not raw_intent.strip():
            raise ActionResponseParseError(raw_response, "intent must be a non-empty string.")
        intent = raw_intent.strip().casefold() if raw_intent.isascii() else raw_intent.strip()
        target = parsed.get("target")
        object_ref = parsed.get("object", parsed.get("object_ref"))
        if target is not None and not isinstance(target, str):
            raise ActionResponseParseError(raw_response, "target must be a string or null.")
        if object_ref is not None and not isinstance(object_ref, str):
            raise ActionResponseParseError(raw_response, "object must be a string or null.")
        parameters = parsed.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise ActionResponseParseError(raw_response, "parameters must be a JSON object.")
        try:
            return ActionIntent(actor_id, player_text, intent, target, object_ref, parameters)
        except (TypeError, ValueError) as error:
            raise ActionResponseParseError(raw_response, str(error)) from error

    def generate_narrative(self, event: WorldEvent, agent_context: AgentContext, *, authority_context: Mapping | None = None) -> str:
        if not isinstance(event, WorldEvent):
            raise TypeError("event must be a WorldEvent.")
        if not isinstance(agent_context, AgentContext):
            raise TypeError("agent_context must be an AgentContext.")
        safe_context = {
            "character_id": agent_context.character_id,
            "authority_level": "PLAYER",
            "allowed_information": ("self", "public", "owned_knowledge"),
            "excluded_information": ("complete_world_state", "hidden_knowledge", "hidden_motivation"),
        }
        if authority_context is not None:
            if not isinstance(authority_context, Mapping) or authority_context.get("character_id") != agent_context.character_id:
                raise ValueError("authority_context must belong to the narrative observer.")
            safe_context = dict(authority_context)
        return self._call(AIGMRequest("generate_narrative", {
            "event": event,
            "character_id": agent_context.character_id,
            "authority_context": safe_context,
        })).content

    def generate_dialogue(
        self,
        speaker_context: AgentContext,
        target_context: AgentContext | None,
        situation: str,
        *,
        character_mind: CharacterMind | None = None,
        knowledge_context: KnowledgeContext | None = None,
        current_scene: Mapping | None = None,
        player_visible_information: tuple[str, ...] = (),
        authority_context: Mapping | None = None,
        cognitive_context: Mapping | None = None,
    ) -> str:
        if not isinstance(speaker_context, AgentContext):
            raise TypeError("speaker_context must be an AgentContext.")
        if target_context is not None and not isinstance(target_context, AgentContext):
            raise TypeError("target_context must be an AgentContext or None.")
        if not isinstance(situation, str) or not situation.strip():
            raise ValueError("situation must not be empty.")
        if character_mind is None:
            character_mind = _mind_from_agent_context(speaker_context)
        elif not isinstance(character_mind, CharacterMind):
            raise TypeError("character_mind must be a CharacterMind or None.")
        if current_scene is not None and not isinstance(current_scene, Mapping):
            raise TypeError("current_scene must be a mapping or None.")
        if knowledge_context is not None:
            if not isinstance(knowledge_context, KnowledgeContext):
                raise TypeError("knowledge_context must be a KnowledgeContext or None.")
            if knowledge_context.owner_id not in (None, speaker_context.character_id):
                raise ValueError("knowledge_context belongs to a different character.")
            from dataclasses import replace

            character_mind = replace(character_mind, knowledge_context=knowledge_context)
        scene = dict(current_scene or {})
        scene.setdefault("situation", situation)
        speaker_prompt_context = dict(self._context_builder.build(
            character_mind,
            current_scene=scene,
            player_visible_information=player_visible_information,
            character_id=speaker_context.character_id,
            knowledge_query=situation,
            cognitive_context=cognitive_context,
        ))
        if authority_context is not None:
            if not isinstance(authority_context, Mapping):
                raise TypeError("authority_context must be a mapping or None.")
            if authority_context.get("character_id") != speaker_context.character_id:
                raise ValueError("authority_context must belong to the speaker.")
            speaker_prompt_context["authority_context"] = dict(authority_context)
        target_summary = None
        if target_context is not None:
            target_summary = {
                "name": target_context.character_state.name,
                "role": target_context.character_state.role,
            }
        return self._call(
            AIGMRequest(
                "generate_dialogue",
                {
                    "speaker": speaker_prompt_context,
                    "target": target_summary,
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


def _authority_from_context(context, character_id):
    if isinstance(context, Mapping):
        value = context.get("authority_context")
        if isinstance(value, Mapping) and value.get("character_id") == character_id:
            return dict(value)
    return {
        "character_id": character_id,
        "authority_level": "PLAYER",
        "allowed_information": ("self", "public", "owned_knowledge"),
        "excluded_information": ("complete_world_state", "hidden_knowledge", "hidden_motivation"),
    }


def _mind_from_agent_context(context: AgentContext) -> CharacterMind:
    """Make a safe baseline mind when no richer CharacterCard mind was supplied."""
    character = context.character_state
    return CharacterMind(
        identity=Identity(character.name, character.role),
        personality=PersonalityProfile(
            traits=character.traits,
            goals=character.goals,
            fears=character.fears,
        ),
        speech_style=SpeechStyle(),
        memory_context=MemoryContext(
            stable_memory=character.memories,
            relationship_memory=tuple(
                f"关系类型：{item.relation_type}，信任度：{item.trust:.2f}"
                for item in context.relationships
                if item.source_id == context.character_id
            ),
            recent_memory=tuple(memory.content for memory in context.memories),
        ),
    )


def _extract_json_object(raw_response: str) -> tuple[dict | None, str]:
    """Extract the first valid JSON object, including fenced or prose-wrapped JSON."""
    stripped = raw_response.strip()
    if not stripped:
        return None, "response is empty."

    candidates: list[str] = []
    for match in re.finditer(r"```(?:json)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL):
        candidates.append(match.group(1).strip())
    candidates.append(stripped)

    last_reason = "no JSON object found."
    for candidate_text in candidates:
        for candidate in _balanced_json_objects(candidate_text):
            try:
                value = json.loads(candidate)
            except json.JSONDecodeError as error:
                last_reason = f"invalid JSON object (line {error.lineno}, column {error.colno})."
                continue
            if isinstance(value, dict):
                return value, ""
            last_reason = "JSON value must be an object."
    return None, last_reason


def _balanced_json_objects(text: str):
    """Yield brace-balanced object candidates while respecting JSON strings."""
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if start is None:
            if char == "{":
                start = index
                depth = 1
                in_string = False
                escaped = False
            continue

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                yield text[start : index + 1]
                start = None


def _first_present(payload: dict, *keys: str):
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


_ACTION_ALIASES = {
    "observe": "observe",
    "observation": "observe",
    "look": "observe",
    "inspect": "observe",
    "观察": "observe",
    "看看": "observe",
    "查看": "observe",
    "help": "help",
    "assist": "help",
    "帮助": "help",
    "救": "help",
    "救助": "help",
    "protect": "protect",
    "guard": "protect",
    "保护": "protect",
    "守护": "protect",
}


def _normalise_action_label(label: str) -> str | None:
    normalized = label.strip().strip("`\"'，。:： ").casefold()
    exact = _ACTION_ALIASES.get(normalized)
    if exact is not None:
        return exact

    # English action labels are accepted only as labels, never as incidental
    # words in an explanation (for example, "do not observe").
    english_label = normalized.replace("_", " ").replace("-", " ")
    if re.fullmatch(r"(?:observe|observation|look|inspect|help|assist|protect|guard)(?: action)?", english_label):
        return _ACTION_ALIASES[english_label.removesuffix(" action")]

    # Chinese models often return short action phrases instead of enum values.
    # Reject negated prose and any line that mentions more than one action kind.
    if any(term in normalized for term in ("不", "不要", "无需", "拒绝", "不能")):
        return None
    matches = {
        action
        for alias, action in _ACTION_ALIASES.items()
        if not alias.isascii() and alias in normalized
    }
    return next(iter(matches)) if len(matches) == 1 else None


def _infer_action_from_text(raw_response: str) -> str | None:
    found: set[str] = set()
    for line in raw_response.splitlines():
        candidate = line.strip().strip("`*#>- ")
        field_match = re.search(
            r"(?:action_type|intent|action)\s*[\"']?\s*[:=]\s*[\"']?([^\"',}]+)",
            candidate,
            flags=re.IGNORECASE,
        )
        label = field_match.group(1).strip() if field_match else candidate
        intent = _normalise_action_label(label)
        if intent is not None:
            found.add(intent)
    if not found:
        # Handle a one-line prose answer, but reject answers mentioning
        # multiple possible actions.
        intent = _normalise_action_label(raw_response)
        if intent is not None:
            found.add(intent)
    return next(iter(found)) if len(found) == 1 else None


def _normalise_target(target: str) -> str:
    normalized = target.strip().casefold()
    if normalized in {"doctor", "医生"}:
        return "doctor"
    if normalized in {"soldier", "士兵"}:
        return "soldier"
    return target.strip()


def _infer_target(raw_response: str) -> str | None:
    normalized = raw_response.casefold()
    if re.search(r"\bdoctor\b", normalized) or "医生" in normalized:
        return "doctor"
    if re.search(r"\bsoldier\b", normalized) or "士兵" in normalized:
        return "soldier"
    return None
