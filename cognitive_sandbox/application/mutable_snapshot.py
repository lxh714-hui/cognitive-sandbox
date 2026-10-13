from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy


def mutable_snapshot(value):
    """Copy read-only mapping trees into ordinary isolated Python containers."""
    if isinstance(value, Mapping):
        return {mutable_snapshot(key): mutable_snapshot(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(mutable_snapshot(item) for item in value)
    if isinstance(value, list):
        return [mutable_snapshot(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return {mutable_snapshot(item) for item in value}
    return deepcopy(value)
