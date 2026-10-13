from enum import Enum


class ConstraintType(str, Enum):
    PREFER = "PREFER"
    AVOID = "AVOID"
    FORBID = "FORBID"
