import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from cognitive_sandbox.narrative.opportunity import NarrativeOpportunity
from cognitive_sandbox.presentation.main_window import FoundationMainWindow
from cognitive_sandbox.presentation.story_mode.story_view import StoryView


def test_player_can_ignore_opportunity_or_prepare_a_suggested_action():
    app = QApplication.instance() or QApplication([])
    window = FoundationMainWindow()
    opportunity = NarrativeOpportunity(
        "op-player", "INFORMATION", visibility="owner", visible_character_ids=("player",),
        description="你听到一条关于街区的传闻。",
        possible_actions=("前往街区", "暂时忽略"), importance=.8,
    )
    window.set_narrative_opportunities((opportunity,), focus="玩家 · 街区")
    assert not window.guidance_panel.isHidden()
    assert "值得注意" in window.guidance_focus.text()
    buttons = window.guidance_panel.findChildren(type(window.confirm_button))
    next(button for button in buttons if button.text() == "前往街区").click()
    assert window.player_input.toPlainText() == "前往街区"
    assert window.message_history == []
    window.close()


def test_story_view_shows_only_significant_player_visible_opportunities():
    app = QApplication.instance() or QApplication([])
    from cognitive_sandbox.application.game_launcher import GameLauncher

    session = GameLauncher().start_world("anchor")
    significant = NarrativeOpportunity(
        "op-story", "INFORMATION", visibility="owner", visible_character_ids=(session.player_id,),
        description="一条你亲自听到的传闻值得核实。", importance=.8,
    )

    class Service:
        def for_character(self, character_id, *, limit=None):
            assert character_id == session.player_id
            return (significant,)

    session.opportunity_service = Service()
    view = StoryView(session, runner=object())
    assert "值得注意" in view.opportunity_summary.text()
    assert "你亲自听到的传闻" in view.opportunity_summary.text()
    view.close()
