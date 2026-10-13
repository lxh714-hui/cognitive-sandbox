from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import uuid4

from cognitive_sandbox.domain.ai_gm import AIGMRequest
from cognitive_sandbox.domain.character_card import CharacterCard
from cognitive_sandbox.domain.world_patch import CharacterAddition, WorldPatch, WorldPatchType


class WorldPatchDrafter:
    """Draft a character patch. Model output is data for review, never applied here."""

    def __init__(self, provider=None) -> None:
        if provider is not None and not callable(getattr(provider, "complete", None)):
            raise TypeError("provider must provide complete().")
        self.provider = provider

    def draft_character(self, prompt: str, *, effective_time: str = "当前") -> WorldPatch:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be empty.")
        content = self._model_draft(prompt, effective_time) if self.provider is not None else None
        model_used = content is not None
        if content is None:
            content = self._fallback_draft(prompt)
        card = CharacterCard(
            character_id=f"character_{uuid4().hex}",
            name=content["name"],
            occupation=content["occupation"],
            personality=tuple(content["personality"]),
            background=content["background"],
            goals=tuple(content["goals"]),
        )
        addition = CharacterAddition(
            character_card=card,
            introduction_method=content["introduction_method"],
            appearance_condition=content["appearance_condition"],
            entry_event=content["entry_event"],
        )
        return WorldPatch(
            id=f"patch_{uuid4().hex}",
            type=WorldPatchType.CHARACTER_ADDITION,
            title=f"加入角色：{card.name}",
            description=prompt.strip(),
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            effective_time=effective_time,
            source="AI草案（待用户确认）" if model_used else "规则草案（待用户确认）",
            payload=addition,
        )

    def _model_draft(self, prompt: str, effective_time: str) -> dict | None:
        request = AIGMRequest(
            "draft_world_character_patch",
            {
                "user_request": prompt,
                "effective_time": effective_time,
                "constraints": [
                    "Return only JSON with name, occupation, personality, background, goals, introduction_method, appearance_condition, entry_event.",
                    "Do not claim the character existed in the world's past.",
                    "The character enters no earlier than effective_time.",
                    "Do not describe any event outcome as guaranteed.",
                ],
            },
        )
        response = self.provider.complete(request)
        raw = getattr(response, "content", "")
        if not isinstance(raw, str):
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group())
        except json.JSONDecodeError:
            return None
        required = ("name", "occupation", "background", "introduction_method", "appearance_condition", "entry_event")
        if not isinstance(value, dict) or any(not isinstance(value.get(key), str) or not value[key].strip() for key in required):
            return None
        for key in ("personality", "goals"):
            if not isinstance(value.get(key), list) or any(not isinstance(item, str) or not item.strip() for item in value[key]):
                return None
        return value

    @staticmethod
    def _fallback_draft(prompt: str) -> dict:
        role_match = re.search(r"(?:加入|新增|添加)(?:一个|一名|一位)?(.+?)(?:角色|人物)?$", prompt.strip())
        role = role_match.group(1).strip(" ，,。的人物") if role_match else "新来者"
        if not role:
            role = "新来者"
        return {
            "name": role,
            "occupation": role,
            "personality": ["谨慎"],
            "background": prompt.strip(),
            "goals": ["寻找立足之处"],
            "introduction_method": "通过一条新的入场事件引入",
            "appearance_condition": "补丁确认后，从当前时间点开始生效",
            "entry_event": f"{role}在当前时间点抵达当前地点",
        }
