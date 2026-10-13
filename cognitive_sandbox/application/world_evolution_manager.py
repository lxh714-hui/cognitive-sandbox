from __future__ import annotations

from cognitive_sandbox.application.consistency_checker import ConsistencyChecker
from cognitive_sandbox.application.world_library import WorldLibrary
from cognitive_sandbox.domain.patch_validation_result import PatchValidationResult, PatchValidationStatus
from cognitive_sandbox.domain.world_patch import WorldPatch


class WorldEvolutionManager:
    """Validate and explicitly confirm append-only additions to a world instance."""

    def __init__(self, world_library: WorldLibrary, checker: ConsistencyChecker | None = None) -> None:
        if not isinstance(world_library, WorldLibrary):
            raise TypeError("world_library must be a WorldLibrary.")
        self.world_library = world_library
        self.checker = checker or ConsistencyChecker()

    def validate(self, instance_id: str, patch: WorldPatch) -> PatchValidationResult:
        return self.checker.check(
            patch,
            existing_character_ids=self.world_library.character_ids_for(instance_id),
            historical_facts=self.world_library.historical_facts_for(instance_id),
            current_day=self.world_library.current_day_for(instance_id),
        )

    def apply(
        self, instance_id: str, patch: WorldPatch, *, confirmed: bool = False
    ) -> PatchValidationResult:
        result = self.validate(instance_id, patch)
        if result.status is PatchValidationStatus.REJECTED:
            return result
        if not confirmed:
            if result.status is PatchValidationStatus.NEEDS_CONFIRMATION:
                return result
            return PatchValidationResult(
                PatchValidationStatus.NEEDS_CONFIRMATION,
                ("补丁草案尚未确认；确认后才会加入该世界。",),
            )
        self.world_library.append_patch(instance_id, patch)
        return PatchValidationResult(PatchValidationStatus.SUCCESS, result.reasons)
