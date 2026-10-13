from cognitive_sandbox.conflict import ConflictManager, ConflictSnapshot, ConflictState, ConflictStatus, ConflictType


def test_conflicts_can_resolve_transform_or_be_accepted():
    manager = ConflictManager(ConflictSnapshot((
        ConflictState("r", ConflictType.GOAL_CONFLICT, ("a", "b")),
        ConflictState("t", ConflictType.INFORMATION_CONFLICT, ("a", "b")),
        ConflictState("a", ConflictType.RESOURCE_CONFLICT, ("a", "b")),
    )))
    assert manager.resolve("r").status is ConflictStatus.RESOLVED
    manager.resolve("t", outcome="transformed")
    assert manager.transformed_count == 1
    assert manager.resolve("a", outcome="accepted").status is ConflictStatus.ACCEPTED
