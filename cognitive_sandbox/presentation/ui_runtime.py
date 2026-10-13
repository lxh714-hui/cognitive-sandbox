from __future__ import annotations

from cognitive_sandbox.application.roleplay_session import RoleplaySession
from cognitive_sandbox.domain.player_interaction import InteractionSource, PlayerInteraction
from cognitive_sandbox.domain.roleplay_result import RoleplayResult
from cognitive_sandbox.presentation.scenario_presenter import ScenarioPresenter


class UIRuntime:
    """Connect the desktop window to the unified interaction pipeline."""

    def __init__(self, window, session: RoleplaySession, *, show_opening: bool = True) -> None:
        if not callable(getattr(window, "append_narrative_event", None)):
            raise TypeError("window must provide append_narrative_event.")
        if not callable(getattr(window, "append_dialogue_line", None)):
            raise TypeError("window must provide append_dialogue_line.")
        if not isinstance(session, RoleplaySession):
            raise TypeError("session must be a RoleplaySession.")
        self.window = window
        self.session = session
        self.last_result: RoleplayResult | None = None
        self._scenario_presenter = ScenarioPresenter()
        opening_marker = getattr(window, "_opening_session_id", None)
        if show_opening and opening_marker != id(session):
            append_opening = getattr(window, "append_opening_message", None)
            if callable(append_opening):
                append_opening(self._scenario_presenter.opening(session))
            try:
                window._opening_session_id = id(session)
            except Exception:
                pass
        if self.session.current_turn is None:
            self.session.start()
        attach = getattr(window, "set_ui_runtime", None)
        if callable(attach):
            attach(self)
        self.refresh_guidance()

    def handle_player_input(self, text: str):
        turn = self.session.current_turn
        if turn is None or turn.status == "completed":
            self.session.start()
        return self.session.submit_interaction(PlayerInteraction(
            actor_id=self.session.player_id,
            intent="unparsed",
            source=InteractionSource.TEXT,
            raw_input=text,
        ))

    def handle_confirm(self) -> tuple[str, str]:
        result = self.execute_confirm()
        return self.present_result(result)

    def execute_confirm(self) -> RoleplayResult:
        """Execute the pending turn without touching presentation widgets.

        FoundationMainWindow calls this method from RoleplayWorker. Keeping
        result rendering separate ensures all Qt updates happen on the UI thread.
        """
        return self.session.confirm()

    def recover_failed_execution(self) -> None:
        """Allow a fresh turn after an executor raised before completing one."""
        self.session.current_turn = None
        self.session.pending_interaction = None

    def present_result(self, result: RoleplayResult) -> tuple[str, str]:
        self.last_result = result
        clear_status = getattr(self.window, "clear_system_message", None)
        if callable(clear_status):
            clear_status()
        presented = self._display_result(result)
        self.refresh_guidance()
        return presented

    def refresh_guidance(self):
        """Refresh the player-scoped guidance snapshot without changing runtime state."""
        service = getattr(self.session, "opportunity_service", None)
        render = getattr(self.window, "set_narrative_opportunities", None)
        if service is None or not callable(render):
            return ()
        opportunities = service.for_character(self.session.player_character_id, limit=3)
        render(opportunities)
        return opportunities

    def prepare_interaction_button(self, intent: str) -> str:
        """Prepare a trusted shortcut interaction without executing it."""
        labels = {"wait": "等待一段时间", "observe": "观察周围"}
        if intent not in labels:
            raise ValueError("unsupported interaction button")
        text = labels[intent]
        turn = self.session.current_turn
        if turn is None or turn.status == "completed":
            self.session.start()
        self.session.submit_interaction(PlayerInteraction(
            actor_id=self.session.player_id,
            intent=intent,
            source=InteractionSource.BUTTON,
            raw_input=text,
        ))
        return text

    def execute_interaction_button(self, intent: str) -> tuple[RoleplayResult, str]:
        text = self.prepare_interaction_button(intent)
        return self.execute_confirm(), text

    def handle_interaction_button(self, intent: str) -> tuple[str, str]:
        """Synchronous compatibility entry point for non-UI callers."""
        text = self.prepare_interaction_button(intent)
        append_player = getattr(self.window, "append_player_message", None)
        if callable(append_player):
            append_player(text)
        result = self.execute_confirm()
        self.last_result = result
        return self._display_result(result)

    def _display_result(self, result: RoleplayResult) -> tuple[str, str]:
        events = tuple(getattr(result.simulation_result, "events", ())) if result.simulation_result else ()
        by_id = {event.event_id: event for event in events}
        observed_ids = {
            event.event_id for event in events
            if event.event_type in {"observe_action", "observation_event"}
        }
        narrative_parts = []
        for narrative in result.narrative_events:
            source = by_id.get(narrative.source_event_id)
            if source is not None and source.event_type in {"observation_event", "observe_action"} and "observations" in source.payload:
                lines = tuple(source.payload.get("observations", ()))
                text = "\n".join(lines)
                append = getattr(self.window, "append_observation_feedback", None)
                if callable(append):
                    append(text)
                else:
                    self.window.append_narrative_event(narrative)
            elif narrative.source_event_id in observed_ids:
                text = self._scenario_presenter.observation(self.session).removeprefix("你环顾四周。\n")
                append = getattr(self.window, "append_observation_feedback", None)
                if callable(append):
                    append(text)
                else:
                    self.window.append_narrative_event(narrative)
            else:
                text = narrative.description
                self.window.append_narrative_event(narrative)
            narrative_parts.append(text)
        for line in result.dialogue_lines:
            self.window.append_dialogue_line(line)
        if not result.action_executed:
            show_message = getattr(self.window, "append_system_message", None)
            if callable(show_message):
                show_message(
                    result.system_message
                    or "这个行动目前无法直接执行。请描述你想做什么，或者补充目标人物、地点或物品。"
                )
        return "\n".join(narrative_parts), "\n".join(line.text for line in result.dialogue_lines)
