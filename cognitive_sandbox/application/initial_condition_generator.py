from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from cognitive_sandbox.domain.initial_conditions import (
    InitialConditionRequest,
    InitialConditionResult,
)


class InitialConditionGenerator:
    """Map a short setting description to deterministic starter world data."""

    def __init__(self, *, world_id_factory: Callable[[], str] | None = None) -> None:
        self._world_id_factory = world_id_factory or (lambda: f"world_{uuid4().hex}")

    def generate(self, request: InitialConditionRequest) -> InitialConditionResult:
        if not isinstance(request, InitialConditionRequest):
            raise TypeError("request must be an InitialConditionRequest.")

        prompt = request.prompt.strip().casefold()
        if any(keyword in prompt for keyword in ("末日城市", "末日后的城市", "废土城市", "post-apocalyptic city")):
            summary = "末日后的城市，危险与稀缺资源并存。"
            state = {
                "setting": "post_apocalypse",
                "danger_level": "medium",
                "resources": "limited",
            }
        else:
            summary = f"一个以“{request.prompt.strip()}”为主题的世界。"
            state = {
                "setting": "generic",
                "description": request.prompt.strip(),
                "danger_level": "low",
                "resources": "standard",
            }

        world_id = self._world_id_factory()
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world_id_factory must return a non-empty string.")
        return InitialConditionResult(
            world_id=world_id,
            summary=summary,
            initial_state=state,
        )
