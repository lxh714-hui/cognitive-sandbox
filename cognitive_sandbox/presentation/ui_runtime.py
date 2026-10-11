from __future__ import annotations

from cognitive_sandbox.application.roleplay_session import RoleplaySession
from cognitive_sandbox.domain.roleplay_result import RoleplayResult


class UIRuntime:
    """Connect the desktop window to a roleplay session without owning simulation rules."""

    def __init__(self, window, session: RoleplaySession) -> None:
        if not callable(getattr(window, "append_narrative_event", None)):
            raise TypeError("window must provide append_narrative_event.")
        if not callable(getattr(window, "append_dialogue_line", None)):
            raise TypeError("window must provide append_dialogue_line.")
        if not isinstance(session, RoleplaySession):
            raise TypeError("session must be a RoleplaySession.")
        self.window = window
        self.session = session
        self.last_result: RoleplayResult | None = None
        if self.session.current_turn is None:
            self.session.start()
        attach = getattr(window, "set_ui_runtime", None)
        if callable(attach):
            attach(self)

    def handle_player_input(self, text: str):
        turn = self.session.current_turn
        if turn is None or turn.status == "completed":
            self.session.start()
        return self.session.submit_input(text)

    def handle_confirm(self) -> tuple[str, str]:
        result = self.session.confirm()
        self.last_result = result
        if not result.action_executed:
            show_message = getattr(self.window, "append_system_message", None)
            if callable(show_message):
                show_message("暂时无法识别这个行动。可以尝试“观察周围”“帮助医生”或“保护士兵”。")
        for event in result.narrative_events:
            self.window.append_narrative_event(event)
        for line in result.dialogue_lines:
            self.window.append_dialogue_line(line)
        narrative_text = "\n".join(
            f"{event.title}\n{event.description}" for event in result.narrative_events
        )
        dialogue_text = "\n".join(line.text for line in result.dialogue_lines)
        return narrative_text, dialogue_text
