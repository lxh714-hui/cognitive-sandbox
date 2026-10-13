import pytest

from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.authority import AuthorityError, AuthorityLevel


def test_director_may_propose_direction_but_cannot_force_control_or_actions():
    session = GameLauncher().start_scenario("example_world")
    manager = session.authority_manager
    assert manager.check_director_permission("create_constraint")
    assert not manager.check_director_permission("force_action")
    assert not manager.check_director_permission("view_hidden_knowledge")
    with pytest.raises(AuthorityError):
        manager.require_director_permission("control_character")
    with pytest.raises(AuthorityError):
        manager.require_director_permission("create_constraint", requester_level=AuthorityLevel.PLAYER)
    result = session.director_manager.submit_text("促进角色相遇")
    assert result.constraint is not None
    assert session.director_manager.constraints
