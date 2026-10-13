from __future__ import annotations

import re

from cognitive_sandbox.domain.action_intent import ActionIntent


class ActionIntentParser:
    """Small deterministic fallback for common Chinese roleplay phrasing."""

    def __init__(self, entity_aliases=None, location_aliases=None, action_defaults=None):
        self.entity_aliases = dict(entity_aliases or {})
        self.location_aliases = dict(location_aliases or {})
        self.action_defaults = dict(action_defaults or {})

    def with_scenario_config(self, scenario_config):
        config = scenario_config or {}
        return ActionIntentParser(
            config.get("entity_aliases", {}), config.get("location_aliases", {}),
            config.get("action_defaults", {}),
        )

    def parse(self, actor_id: str, raw_input: str) -> ActionIntent | None:
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("actor_id must not be empty.")
        if not isinstance(raw_input, str):
            raise TypeError("raw_input must be a string.")
        text = raw_input.strip()
        if not text:
            return None

        if any(term in text for term in (
            "然后呢", "接下来呢", "我不知道该干什么", "不知道该干什么",
            "不知道做什么", "我该做什么", "有什么值得注意", "有什么线索",
        )):
            return ActionIntent(actor_id, raw_input, "seek_guidance")

        intent = self._intent(text)
        if intent is None:
            return None
        target, obj, parameters = self._entities(text, intent)
        if target is not None:
            target = self.entity_aliases.get(target.casefold(), target)
        if obj is not None and intent in {"move", "explore"}:
            for alias, destinations in self.location_aliases.items():
                choices = destinations if isinstance(destinations, (tuple, list)) else (destinations,)
                if alias.casefold() == obj.casefold() and choices:
                    obj = choices[0]
                    break
        if intent in {"observe", "inspect"} and any(
            token in text for token in ("偷偷", "悄悄", "暗中", "不被发现")
        ):
            parameters["method"] = "stealth"
            parameters["risk"] = 0.75
            if target is None:
                match = re.search(r"(?:观察|查看|盯着|留意)([^，。！？\s]{1,16})", text)
                if match:
                    target = match.group(1).strip("的") or None
        if any(term in text for term in ("累了", "有点累", "疲惫")):
            parameters["emotion"] = "tired"
        if any(term in text for term in ("不想再提", "不想提起", "别再提", "不愿谈起")):
            parameters["conversation_preference"] = "avoid_topic"
            if intent == "observe":
                intent = "talk"
        return ActionIntent(actor_id, raw_input, intent, target, obj, parameters)

    @staticmethod
    def _intent(text: str) -> str | None:
        if any(term in text for term in ("然后呢", "接下来呢", "我不知道该干什么", "不知道该干什么", "不知道做什么", "我该做什么")):
            return "seek_guidance"
        if any(term in text for term in ("休息", "歇一会", "歇一下", "睡觉", "躺一会", "回房间")):
            return "rest"
        if any(term in text for term in ("探索", "逛逛", "找找异常", "去街上看看", "出去看看", "四处看看")):
            return "explore"
        if any(term in text for term in ("不想再提", "不想提起", "别再提", "不愿谈起")):
            return "talk"
        if any(term in text for term in ("起床", "醒来", "起身")):
            return "wake"
        if any(term in text for term in ("吃饭", "吃点东西", "用餐", "吃东西")):
            return "eat"
        if any(term in text for term in ("上班", "工作", "处理工作")):
            return "work"
        if any(term in text for term in ("回家", "回住所", "回住处")):
            return "go_home"
        if any(term in text for term in ("等待", "等一会", "等一下", "稍后再说")):
            return "wait"
        if any(term in text for term in ("保护", "守护", "挡在", "掩护")):
            return "protect"
        if any(term in text for term in ("帮助", "帮忙", "救助", "救一下", "扶起", "包扎")):
            return "help"
        if any(term in text for term in ("交谈", "聊天", "聊聊", "聊几句", "说话", "谈谈", "打招呼", "交流")):
            return "talk"
        if any(term in text for term in ("找", "寻找", "联系", "拜访")):
            return "find"
        if any(term in text for term in ("询问", "问问", "问一下", "问", "打听")):
            return "ask"
        if any(term in text for term in ("拿起", "拿走", "拾起", "捡起", "带上")):
            return "take"
        if any(term in text for term in ("给", "交给", "递给")):
            return "give"
        if any(term in text for term in ("使用", "启动", "打开", "操作")):
            return "use"
        if any(term in text for term in ("检查", "调查", "搜查", "仔细查看")):
            return "inspect"
        # Inspect only explicit object-viewing verbs. "偷偷观察某人" remains
        # an observation action, while "看看钟" is an inspection.
        for verb in ("看看", "看一看", "查看"):
            index = text.find(verb)
            if index < 0:
                continue
            remainder = text[index + len(verb):].lstrip("的 ")
            if remainder and not remainder.startswith(("附近", "周围", "周边", "四周", "这里", "周遭", "前方", "前面", "远处")):
                return "inspect"
        if any(term in text for term in ("去", "前往", "走到", "赶往", "离开", "进入")):
            if any(term in text for term in ("看看", "观察", "环顾", "查看")):
                return "move"
            return "move"
        if any(term in text for term in ("观察", "看看", "看一看", "查看", "环顾", "瞧瞧")):
            return "observe"
        return None

    def _entities(self, text: str, intent: str) -> tuple[str | None, str | None, dict]:
        target = None
        object_ref = None
        if intent in {"talk", "ask", "help", "protect", "give", "find"}:
            match = re.search(r"(?:和|跟|向|对|帮助|保护|给|递给|寻找|找|联系|拜访)([^，。！？\s]{1,16}?)(?:交谈|聊天|聊聊|聊几句|说话|谈谈|交流|询问|问问|问一下|打招呼|帮忙|帮助|救助|救一下|扶起|保护|守护|$)", text)
            if match:
                target = match.group(1).strip("的") or None
        if intent == "ask" and target is None:
            ask = re.search(r"(?:询问|问问|问一下|问|打听)(.+)", text)
            remainder = ask.group(1) if ask else ""
            alias = next((name for name in sorted(self.entity_aliases, key=len, reverse=True)
                          if name and name in remainder), None)
            if alias is not None:
                target = self.entity_aliases[alias]
            match = re.match(r"([^，。！？\s]{1,8}?)(?:关于|有关|有没有|是否|什么|怎么|为何|为什么)", remainder)
            if target is None and match:
                target = match.group(1).strip("的") or None
        if intent == "move":
            match = re.search(r"(?:去|前往|走到|赶往|进入)([^，。！？\s]{1,20})", text)
            if match:
                object_ref = re.sub(r"(看看|观察|环顾|查看)$", "", match.group(1)).strip("的") or None
            elif any(phrase in text for phrase in ("离开房间", "离开这里", "出去")):
                destination = self.action_defaults.get("leave_destination")
                object_ref = destination if isinstance(destination, str) and destination.strip() else None
        elif intent == "explore":
            match = re.search(r"(?:去|前往|到|走到|出去)([^，。！？\s]{1,20}?)(?:看看|观察|探索|瞧瞧|找找|$)", text)
            if match:
                object_ref = match.group(1).strip("的") or None
        elif intent in {"inspect", "use", "take", "give"}:
            match = re.search(r"(?:看看|看一看|查看|检查|调查|搜查|仔细查看|使用|启动|打开|操作|拿起|拿走|拾起|捡起|带上)([^，。！？\s]{1,20})", text)
            if match:
                object_ref = match.group(1).strip("的") or None
        parameters = {}
        if intent == "talk" and any(term in text for term in ("不想再提", "不想提起", "别再提", "不愿谈起")):
            topic_match = re.search(r"(?:提起|提|谈起)([^，。！？\s]{1,20})", text)
            if topic_match:
                parameters["topic"] = topic_match.group(1).strip("的那件事")
            parameters["conversation_preference"] = "avoid_topic"
        if intent == "move" and any(term in text for term in ("看看", "观察", "环顾", "查看")):
            parameters["follow_up_intent"] = "observe"
        if intent in {"talk", "ask"}:
            topic_match = re.search(r"(?:关于|有关)([^，。！？\s]{1,30})", text)
            topic_text = topic_match.group(1) if topic_match else ""
            if not topic_text and intent == "ask" and target:
                target_alias = next((name for name in sorted(self.entity_aliases, key=len, reverse=True)
                                     if name and name in text), target)
                target_position = text.find(target_alias)
                if target_position >= 0:
                    topic_text = text[target_position + len(target_alias):]
            if topic_text:
                topic = topic_text.strip("的事情吗？?事情况 ")
                if topic and topic != target:
                    parameters["topic"] = topic
        return target, object_ref, parameters
