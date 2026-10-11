from __future__ import annotations


def build_world_generation_prompt(
    user_prompt: str,
    *,
    min_characters: int = 3,
    max_characters: int = 5,
    min_events: int = 1,
    max_events: int = 3,
) -> str:
    """Build instructions for a strict, content-only world draft."""

    return f"""根据用户描述生成一个世界内容草稿。只返回严格 JSON，不要 Markdown 代码块、注释或 JSON 之外的文字。

根对象必须且只能包含 world、characters、events 三个字段，格式如下：
{{
  "world": {{"world_id": "...", "name": "...", "description": "...", "history": [], "rules": []}},
  "characters": [{{"character_id": "...", "name": "...", "identity": {{"age": null, "gender": "", "occupation": ""}}, "personality": [], "background": "", "goals": [], "constraints": [{{"type": "hard", "content": "..."}}]}}],
  "events": [{{"event_id": "...", "name": "...", "description": "...", "event_type": "initial", "participants": [], "conditions": [], "effects": [], "priority": 0}}]
}}

生成 {min_characters} 到 {max_characters} 个重要角色，以及 {min_events} 到 {max_events} 个初始事件。只使用以上字段；identity 只允许 age、gender、occupation、portrait，constraint 只允许 type、content。约束类型只能是 hard、soft、preference。所有集合字段都必须是 JSON 数组。

这是尚待验证和人工确认的内容草稿，不要描述已经运行的模拟结果。不得承诺玩家一定成功，也不得断言某个角色一定死亡；事件 effects 只能描述可能影响，不能写成必然结果。不要加入代码、脚本或其他无法由这些数据模型表达的字段。

用户描述：
{user_prompt}
"""
