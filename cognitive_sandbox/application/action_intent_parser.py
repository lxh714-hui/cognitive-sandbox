from __future__ import annotations

import re

from cognitive_sandbox.domain.action_intent import ActionIntent


class ActionIntentParser:
    """Small deterministic fallback for common Chinese roleplay phrasing."""

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

        if any(term in text for term in (
            "然后呢", "接下来呢", "我不知道该干什么", "不知道该干什么",
            "不知道做什么", "我该做什么", "有什么值得注意", "有什么线索",
        )):
            return ActionIntent(actor_id, raw_input, "seek_guidance")

        intent = self._intent(text)
        if intent is None:
            return None
        target, obj, parameters = self._entities(text, intent)
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
        if any(term in text for term in ("钟", "时钟", "钟表")) and any(
            term in text for term in ("看看", "看一看", "查看", "检查", "观察")
        ):
            return "inspect"
        if any(term in text for term in ("去", "前往", "走到", "赶往", "离开", "进入")):
            if any(term in text for term in ("看看", "观察", "环顾", "查看")):
                return "move"
            return "move"
        if any(term in text for term in ("观察", "看看", "查看", "环顾", "瞧瞧")):
            if any(term in text for term in ("建筑", "房间", "门", "设备", "物品", "箱子")):
                return "inspect"
            return "observe"
        return None

    @staticmethod
    def _entities(text: str, intent: str) -> tuple[str | None, str | None, dict]:
        target = None
        object_ref = None
        if intent in {"talk", "ask", "help", "protect", "give", "find"}:
            match = re.search(r"(?:和|跟|向|对|帮助|保护|给|递给|寻找|找|联系|拜访)([^，。！？\s]{1,16}?)(?:交谈|聊天|聊聊|聊几句|说话|谈谈|交流|询问|问问|问一下|打招呼|帮忙|帮助|救助|救一下|扶起|保护|守护|$)", text)
            if match:
                target = match.group(1).strip("的") or None
        if intent == "ask" and target is None:
            ask = re.search(r"(?:询问|问问|问一下|问|打听)(.+)", text)
            remainder = ask.group(1) if ask else ""
            # Fallback support for common role titles, and arbitrary names when
            # the text clearly separates the person from the topic.
            match = re.search(r"([\u4e00-\u9fff]{0,4}?(?:医生|士兵|商人|幸存者|护士|警卫|队长))", remainder)
            if match:
                target = match.group(1)
            else:
                match = re.match(r"([^，。！？\s]{1,8}?)(?:关于|有关|有没有|是否|什么|怎么|为何|为什么)", remainder)
                if match:
                    target = match.group(1).strip("的") or None
        if intent == "move":
            match = re.search(r"(?:去|前往|走到|赶往|进入)([^，。！？\s]{1,20})", text)
            if match:
                object_ref = re.sub(r"(看看|观察|环顾|查看)$", "", match.group(1)).strip("的") or None
            elif "离开房间" in text:
                object_ref = "街区"
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
                target_position = text.find(target)
                if target_position >= 0:
                    topic_text = text[target_position + len(target):]
            if topic_text:
                topic = topic_text.strip("的事情吗？?事情况 ")
                if topic and topic not in {target, "医生", "士兵"}:
                    parameters["topic"] = topic
        return target, object_ref, parameters
