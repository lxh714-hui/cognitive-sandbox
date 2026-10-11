from __future__ import annotations

from typing import Any

from cognitive_sandbox.application.world_generator import WorldGenerator
from cognitive_sandbox.application.roleplay_session import RoleplaySession as _RoleplaySession
from cognitive_sandbox.domain.scenario_content import ScenarioContent
from cognitive_sandbox.domain.world_generation_result import WorldGenerationResult


class WorldCreationSession:
    """Manage draft, human confirmation, and launch for one generated world."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    STARTED = "STARTED"

    def __init__(self, generator: WorldGenerator, game_launcher: Any) -> None:
        if not callable(getattr(generator, "generate", None)):
            raise TypeError("generator must provide a generate method.")
        if not callable(getattr(game_launcher, "start_scenario_content", None)):
            raise TypeError("game_launcher must provide start_scenario_content.")
        self.generator = generator
        self.game_launcher = game_launcher
        self.state = self.DRAFT
        self.generation_result: WorldGenerationResult | None = None
        self.scenario_content: ScenarioContent | None = None
        self.roleplay_session: _RoleplaySession | None = None

    def generate(self, prompt: str) -> WorldGenerationResult:
        if self.state == self.STARTED:
            raise RuntimeError("a started world creation session cannot generate another draft.")
        result = self.generator.generate(prompt)
        if not isinstance(result, WorldGenerationResult):
            raise TypeError("generator.generate must return a WorldGenerationResult.")
        self.generation_result = result
        self.scenario_content = result.scenario_content if result.validation_result.valid else None
        self.roleplay_session = None
        self.state = self.DRAFT
        return result

    def confirm(self) -> ScenarioContent:
        if self.state != self.DRAFT:
            raise RuntimeError("only a draft can be confirmed.")
        result = self.generation_result
        if result is None or not result.validation_result.valid or result.scenario_content is None:
            raise RuntimeError("there is no valid generated draft to confirm.")
        self.scenario_content = result.scenario_content
        self.state = self.CONFIRMED
        return self.scenario_content

    def start(self) -> _RoleplaySession:
        if self.state != self.CONFIRMED or self.scenario_content is None:
            raise RuntimeError("confirm the generated draft before starting it.")
        session = self.game_launcher.start_scenario_content(self.scenario_content)
        if not isinstance(session, _RoleplaySession):
            raise TypeError("game_launcher must return a RoleplaySession.")
        self.roleplay_session = session
        self.state = self.STARTED
        return session
