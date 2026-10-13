from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from cognitive_sandbox.agency.routine_behavior import RoutineBehavior


def test_daily_routine_produces_generic_action_and_is_immutable():
    routine = RoutineBehavior("pei", "socialize", ("daily",), .2)
    assert routine.is_due(datetime(2030, 1, 1, tzinfo=timezone.utc))
    assert routine.candidate().action_type == "socialize"
    with pytest.raises(FrozenInstanceError):
        routine.priority = .9


def test_hourly_schedule_only_runs_at_matching_time():
    routine = RoutineBehavior("song", "observe", ("hour:09",), .3)
    assert routine.is_due(datetime(2030, 1, 1, 9, tzinfo=timezone.utc))
    assert not routine.is_due(datetime(2030, 1, 1, 10, tzinfo=timezone.utc))
