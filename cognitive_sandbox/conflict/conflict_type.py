from enum import Enum


class ConflictType(str, Enum):
    GOAL_CONFLICT = "goal_conflict"
    RESOURCE_CONFLICT = "resource_conflict"
    INFORMATION_CONFLICT = "information_conflict"
    VALUE_CONFLICT = "value_conflict"
    RELATIONSHIP_CONFLICT = "relationship_conflict"
