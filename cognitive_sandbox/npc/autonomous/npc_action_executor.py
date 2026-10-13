from __future__ import annotations

from uuid import uuid4

from cognitive_sandbox.domain.world_events import WorldEvent
from cognitive_sandbox.application.npc.npc_action import NpcAction


class NpcActionExecutor:
    """Translate a permitted autonomous candidate into an objective event."""

    EVENT_TYPES = {
        "patrol": "npc_patrolled", "collect_material": "npc_materials_collected",
        "repair_clinic": "doctor_repaired_clinic", "socialize": "npc_socialized",
        "investigate": "npc_investigated", "observe": "npc_observed",
        "work": "npc_worked", "rest": "npc_rested", "travel": "npc_traveled",
        "organize": "npc_organized",
    }

    def __init__(self, *, world_id="world", branch_id="main", id_factory=None):
        self.world_id = world_id
        self.branch_id = branch_id
        self._id_factory = id_factory or (lambda: uuid4().hex)

    def execute(self, action: NpcAction, *, timestamp: str | None = None, world_revision: int = 0, actor_name: str | None = None):
        if not isinstance(action, NpcAction):
            raise TypeError("action must be NpcAction.")
        event_type = self.EVENT_TYPES.get(action.action_type)
        if event_type is None:
            return None
        lifecycle, cooldown = {
            "work": ("REPEATABLE", 2), "rest": ("REPEATABLE", 1),
            "organize": ("REPEATABLE", 4), "observe": ("REPEATABLE", 2),
            "socialize": ("REPEATABLE", 2), "investigate": ("REPEATABLE", 3),
            "travel": ("REPEATABLE", 2), "patrol": ("REPEATABLE", 2),
            "collect_material": ("REPEATABLE", 0), "repair_clinic": ("REPEATABLE", 0),
        }.get(action.action_type, ("REPEATABLE", 0))
        importance = {
            "work": 0, "rest": 0, "organize": 0, "observe": 1,
            "socialize": 1, "investigate": 2, "repair_clinic": 3,
            "collect_material": 1, "patrol": 1, "travel": 1,
        }.get(action.action_type, 1)
        return WorldEvent(
            f"event_{self._id_factory()}", self.branch_id, self.world_id, event_type,
            action.actor_id,
            {
                "action_type": action.action_type, "reason": action.reason,
                "parameters": dict(action.parameters), "importance": 0.4,
                "importance_level": importance,
                "event_lifecycle": action.parameters.get("event_lifecycle", lifecycle),
                "cooldown_days": action.parameters.get("cooldown_days", cooldown),
                "lifecycle_key": action.parameters.get("lifecycle_key", event_type),
                "lifecycle_active": action.parameters.get(
                    "lifecycle_active", action.parameters.get("event_lifecycle", lifecycle) == "ONGOING"
                ),
                **({"actor_name": actor_name} if isinstance(actor_name, str) and actor_name.strip() else {}),
                "description": _description(action.action_type),
            },
            world_revision, target_id=action.target,
            location=(action.parameters.get("location") if isinstance(action.parameters.get("location"), str)
                      and action.parameters.get("location").strip() else None),
            timestamp=timestamp,
        )


def _description(action_type):
    return {
        "patrol": "有人开始巡查周边区域。",
        "collect_material": "有人开始收集修复医疗站所需的材料。",
        "repair_clinic": "有人使用收集到的材料修复医疗站。",
        "socialize": "角色与附近的人进行了交谈。",
        "investigate": "角色开始核实自己已知的一条线索。",
        "observe": "角色观察了周围环境。",
        "work": "角色投入了日常工作。",
        "rest": "角色停下来休息了一段时间。",
        "travel": "角色沿着可通行的路线前往另一处地点。",
        "organize": "角色整理了手边的物品或记录。",
    }.get(action_type, "角色采取了一项行动。")
