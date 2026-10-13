from __future__ import annotations

from cognitive_sandbox.application.npc.npc_action import NpcAction


class NpcActionGenerator:
    """Generate rule-based candidates from registered goals and clock state."""

    def generate(self, character_mind, goals, *, current_time, owner_id=None, world_state=None, resource_manager=None):
        owner_id = owner_id or getattr(character_mind, "character_id", None)
        if owner_id is None:
            owner_id = getattr(getattr(character_mind, "knowledge_context", None), "owner_id", None)
        if owner_id is None:
            owner_id = getattr(getattr(character_mind, "relationship_context", None), "owner_id", None)
        if owner_id is None:
            return ()
        result = []
        for goal in sorted(goals, key=lambda item: (-item.priority, item.goal_type)):
            goal_type = goal.goal_type.casefold()
            if goal_type in {"protect_city", "patrol", "guard_area"}:
                if current_time.hour in range(18, 24) or current_time.hour in range(0, 6):
                    result.append(NpcAction(owner_id, "patrol", parameters={"location": (world_state or {}).get("location", "")}, reason="值守目标要求巡查区域"))
            elif goal_type in {"repair_clinic", "restore_medical_station"}:
                if not (world_state or {}).get("clinic_repaired", False):
                    has_materials = resource_manager is not None and resource_manager.quantity("medical_supplies") >= 1
                    result.append(NpcAction(
                        owner_id, "repair_clinic" if has_materials else "collect_material",
                        parameters={"for": "clinic_repair", "location": "clinic"},
                        reason="使用材料修复医疗站" if has_materials else "修复医疗站需要收集材料",
                    ))
            elif goal_type == "collect_materials":
                if resource_manager is None or resource_manager.quantity("medical_supplies") < 1:
                    result.append(NpcAction(owner_id, "collect_material", parameters={"for": "clinic_repair", "location": "clinic"}, reason="收集医疗站修复材料"))
            elif goal_type == "restore_power":
                if resource_manager is not None and resource_manager.quantity("medical_supplies") >= 1:
                    result.append(NpcAction(owner_id, "repair_clinic", parameters={"for": "clinic_repair", "location": "clinic"}, reason="恢复医疗站供电"))
        return tuple(result)

    def generate_for(self, owner_id, goals, *, current_time, world_state=None, resource_manager=None):
        """Convenient ID-based variant for callers that do not carry CharacterMind."""
        return self.generate(None, goals, current_time=current_time, owner_id=owner_id, world_state=world_state, resource_manager=resource_manager)
