from __future__ import annotations

from cognitive_sandbox.domain.scenario import Scenario


def builtin_scenarios() -> tuple[Scenario, ...]:
    return (
        Scenario(
            scenario_id="post_apocalypse_city",
            name="末日城市",
            description="一座在灾后艰难维持生活的城市，危险与资源短缺并存。",
            initial_world_state={"danger_level": 0.5, "resource_level": 0.3},
            character_templates=(
                {
                    "character_id": "doctor",
                    "name": "医生",
                    "role": "doctor",
                    "traits": ("compassionate",),
                    "goals": ("help others",),
                },
                {
                    "character_id": "soldier",
                    "name": "士兵",
                    "role": "soldier",
                    "traits": ("brave",),
                    "goals": ("protect others",),
                },
                {
                    "character_id": "survivor",
                    "name": "幸存者",
                    "role": "survivor",
                    "traits": ("adaptive",),
                    "goals": (),
                },
            ),
        ),
    )
