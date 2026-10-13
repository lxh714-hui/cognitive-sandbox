from __future__ import annotations

import re
from collections.abc import Iterable

from cognitive_sandbox.domain.patch_validation_result import PatchValidationResult, PatchValidationStatus
from cognitive_sandbox.domain.event_card import EventCard
from cognitive_sandbox.domain.world_patch import CharacterAddition, WorldPatch, WorldPatchType


class ConsistencyChecker:
    """Check additions against recorded facts without rewriting any world data."""

    _DAY = re.compile(r"第\s*(\d+)\s*天")
    _NO_MAGIC = ("不存在魔法", "没有魔法", "无魔法", "不允许魔法")
    _MAGIC = ("魔法师", "法师", "魔法", "施法")
    _RETROACTIVE = ("一直", "早已", "自古", "从一开始", "过去就")

    def check(
        self,
        patch: WorldPatch,
        *,
        existing_character_ids: Iterable[str] = (),
        historical_facts: Iterable[str] = (),
        current_day: int | None = None,
    ) -> PatchValidationResult:
        if not isinstance(patch, WorldPatch):
            raise TypeError("patch must be a WorldPatch.")
        facts = tuple(fact for fact in historical_facts if isinstance(fact, str))
        ids = frozenset(existing_character_ids)
        patch_days = [int(value) for value in self._DAY.findall(patch.effective_time)]
        if current_day is not None and patch_days and min(patch_days) < current_day:
            return PatchValidationResult(
                PatchValidationStatus.REJECTED,
                ("补丁生效时间早于当前世界时间；历史只能通过新增事件解释，不能直接改写。",),
            )

        if patch.type is WorldPatchType.CHARACTER_ADDITION:
            addition = patch.payload
            assert isinstance(addition, CharacterAddition)
            if addition.character_card.character_id in ids:
                return PatchValidationResult(
                    PatchValidationStatus.REJECTED,
                    (f"角色 ID 已存在：{addition.character_card.character_id}",),
                )
            card_text = " ".join((addition.character_card.occupation, addition.character_card.background,
                                  *addition.character_card.personality, *addition.character_card.goals))
            if self._has_negative_magic_fact(facts) and self._contains_any(card_text, self._MAGIC):
                return PatchValidationResult(
                    PatchValidationStatus.REJECTED,
                    ("角色设定与世界中‘不存在魔法’的既有事实冲突。",),
                )
            temporal_reason = self._temporal_conflict(addition, facts, current_day)
            if temporal_reason:
                return PatchValidationResult(PatchValidationStatus.REJECTED, (temporal_reason,))

        if patch.type is WorldPatchType.LORE_PATCH:
            payload = patch.payload if isinstance(patch.payload, str) else ""
            if (
                self._has_negative_magic_fact(facts)
                and self._contains_any(payload, self._MAGIC)
                and self._contains_any(payload, self._RETROACTIVE)
            ):
                return PatchValidationResult(
                    PatchValidationStatus.REJECTED,
                    ("追溯性世界设定与既有事实冲突，不能覆盖历史。",),
                )
            return PatchValidationResult(
                PatchValidationStatus.NEEDS_CONFIRMATION,
                ("世界设定补丁需要确认；确认后仅从标注的生效时间开始适用。",),
            )

        if patch.type is WorldPatchType.EVENT_ADDITION:
            event = patch.payload
            assert isinstance(event, EventCard)
            event_days = [int(value) for condition in event.conditions for value in self._DAY.findall(condition)]
            if current_day is not None and event_days and min(event_days) < current_day:
                return PatchValidationResult(
                    PatchValidationStatus.REJECTED,
                    ("新增事件的触发时间早于当前世界时间。",),
                )

        return PatchValidationResult(PatchValidationStatus.SUCCESS)

    def _temporal_conflict(
        self, addition: CharacterAddition, facts: tuple[str, ...], current_day: int | None
    ) -> str | None:
        claim = " ".join((addition.introduction_method, addition.appearance_condition, addition.entry_event))
        claim_days = [int(value) for value in self._DAY.findall(claim)]
        history_days = [int(value) for fact in facts for value in self._DAY.findall(fact)]
        if current_day is not None and claim_days and min(claim_days) < current_day:
            if self._contains_any(claim, self._RETROACTIVE) or "住" in claim or "生活" in claim:
                return "角色加入时间早于当前世界时间，不能补写为既有经历。"

        # A past place destruction/disuse cannot coexist with a claim that the
        # character had always lived there. The event is preserved as-is.
        if self._contains_any(claim, self._RETROACTIVE):
            for fact in facts:
                if not any(token in fact for token in ("废弃", "毁", "坍塌", "关闭")):
                    continue
                fact_day = next((int(value) for value in self._DAY.findall(fact)), None)
                if fact_day is None:
                    continue
                if any(location in fact and location in claim for location in ("医疗中心", "医院", "避难所", "车站", "港口")):
                    if not claim_days or min(claim_days) < fact_day:
                        return f"角色的追溯性经历与既有事实冲突：{fact}"
        return None

    @classmethod
    def _has_negative_magic_fact(cls, facts: tuple[str, ...]) -> bool:
        return any(cls._contains_any(fact, cls._NO_MAGIC) for fact in facts)

    @staticmethod
    def _contains_any(text: str, candidates: tuple[str, ...]) -> bool:
        return any(candidate in text for candidate in candidates)
