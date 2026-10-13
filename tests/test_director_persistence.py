from cognitive_sandbox.application.game_launcher import GameLauncher
from cognitive_sandbox.director import DirectorConstraintStatus
from cognitive_sandbox.persistence.models.save_metadata import SaveMetadata
from cognitive_sandbox.persistence.world_serializer import WorldSerializer


def test_director_constraints_and_history_round_trip_with_legacy_defaults():
    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    result = session.director_manager.submit_text("希望医生早点出现")
    metadata = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world",
                            "灰港纪元", "海港城市", "created", "played")
    serializer = WorldSerializer()
    payload = serializer.serialize_world(metadata, session)
    decoded = serializer.deserialize_world(payload)
    assert decoded["director"]["history"][-1] == result
    restored = launcher.restore_saved_world(decoded)
    assert restored.director_manager.history[-1].constraint.status is DirectorConstraintStatus.SEARCHING
    old = dict(payload)
    old.pop("director")
    assert serializer.deserialize_world(old)["director"] == {"constraints": (), "history": ()}


def test_expanded_constraint_fields_round_trip_and_legacy_constraint_defaults():
    from cognitive_sandbox.director import DirectorConstraint, DirectorIntent, DirectorIntentType
    from cognitive_sandbox.director.constraint_type import ConstraintType
    from cognitive_sandbox.director.constraint_target import ConstraintTarget
    from cognitive_sandbox.director.constraint_strength import ConstraintStrength

    launcher = GameLauncher()
    session = launcher.start_scenario("example_world")
    result = session.director_manager.submit_text("不要让医生过早知道真相")
    meta = SaveMetadata(session.world_instance_id, session.executor.world_id, "example_world", "x", "y", "c", "p")
    serializer = WorldSerializer()
    restored = serializer.deserialize_world(serializer.serialize_world(meta, session))
    saved = restored["director"]["constraints"][-1]
    assert (saved.constraint_type, saved.target_kind, saved.strength) == (
        ConstraintType.AVOID, ConstraintTarget.KNOWLEDGE_REVEAL, ConstraintStrength.MEDIUM)

    legacy_intent = DirectorIntent(DirectorIntentType.CUSTOM_DIRECTION, None, "old")
    legacy = DirectorConstraint("legacy", legacy_intent, None, .5)
    assert legacy.constraint_type is ConstraintType.PREFER
