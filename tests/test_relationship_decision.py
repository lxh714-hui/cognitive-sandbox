from cognitive_sandbox.application.npc.npc_action import NpcAction
from cognitive_sandbox.relationship.lifecycle import RelationshipLifecycleManager
from cognitive_sandbox.relationship.relationship_manager import RelationshipManager
from cognitive_sandbox.relationship.relationship_state import RelationshipState


def test_directional_relationship_changes_action_preference():
    relations = RelationshipManager((RelationshipState("a", "b", trust=80, respect=50),
                                    RelationshipState("b", "a", trust=-70, hostility=60)))
    manager = RelationshipLifecycleManager(relations, character_ids=("a", "b"))
    help_action = NpcAction("a", "help", target="b", reason="test")
    avoid_action = NpcAction("b", "avoid", target="a", reason="test")
    assert manager.action_score_modifier("a", help_action) > 0
    assert manager.action_score_modifier("b", avoid_action) > 0
    assert manager.action_score_modifier("b", NpcAction("b", "help", target="a", reason="test")) < 0

