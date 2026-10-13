import pytest
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QPushButton

from cognitive_sandbox.authority import AuthorityError, AuthorityManager, CharacterAuthority


def test_player_cannot_switch_into_important_character():
    manager = AuthorityManager(
        (CharacterAuthority.player("player"), CharacterAuthority.important_character("liu")),
        player_character_id="player",
    )
    assert manager.check_control_permission("player", requester_id="player")
    assert not manager.check_control_permission("liu", requester_id="player")
    with pytest.raises(AuthorityError, match="cannot be possessed"):
        manager.switch_player_character("liu")


def test_session_identity_cannot_be_switched_to_npc():
    from cognitive_sandbox.application.game_launcher import GameLauncher
    session = GameLauncher().start_scenario("example_world")
    npc_id = next(item.character_id for item in session.agent_contexts if item.character_id != session.player_id)
    with pytest.raises(AuthorityError, match="cannot be possessed"):
        session.switch_player_character(npc_id)


def test_roleplay_action_entry_rejects_important_character_control():
    from cognitive_sandbox.application.game_launcher import GameLauncher
    from cognitive_sandbox.domain.player_interaction import PlayerInteraction
    from cognitive_sandbox.domain.roleplay_turn import RoleplayTurn
    session = GameLauncher().start_scenario("example_world")
    npc = next(item for item in session.agent_contexts if item.character_id != session.player_id)
    turn = RoleplayTurn("attempt", npc.character_id, "executing", "观察周围")
    interaction = PlayerInteraction(npc.character_id, "observe", "BUTTON", "观察周围")
    with pytest.raises(AuthorityError, match="cannot be possessed"):
        session.executor.execute_interaction(
            interaction, turn, npc, session.world_state, session.situation,
            agent_contexts=session.agent_contexts,
        )


def test_character_roster_has_no_enter_or_control_action():
    app = QApplication.instance() or QApplication([])
    from cognitive_sandbox.application.game_launcher import GameLauncher
    from cognitive_sandbox.presentation.character_roster import CharacterRosterDialog
    session = GameLauncher().start_scenario("example_world")
    dialog = CharacterRosterDialog(session)
    assert dialog.characters.count() == len(session.agent_contexts)
    labels = [dialog.characters.item(index).text() for index in range(dialog.characters.count())]
    assert any("当前角色" in item for item in labels)
    assert any("重要人物" in item for item in labels)
    assert not any("进入角色" in button.text() or "控制角色" in button.text()
                   for button in dialog.findChildren(QPushButton))
    dialog.close()
