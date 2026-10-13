from __future__ import annotations


class EncounterInspector:
    """Read-only view of public encounter candidates and recorded contacts."""

    def __init__(self, encounter_manager):
        self.encounter_manager = encounter_manager

    def snapshot(self):
        return tuple({
            "character_a": item.character_a,
            "character_b": item.character_b,
            "location": item.location,
            "reason": item.reason,
            "score": item.score,
            "status": item.status.value,
            "time_window": item.time_window,
        } for item in self.encounter_manager.candidates)

    def render(self):
        rows = self.snapshot()
        if not rows:
            return "当前没有候选相遇。"
        return "\n\n".join(
            f"角色：{row['character_a']}、{row['character_b']}\n地点：{row['location']}\n"
            f"原因：{row['reason']}\n评分：{row['score']:.2f}\n状态：{row['status']}"
            for row in rows
        )
