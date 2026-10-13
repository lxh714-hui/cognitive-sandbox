from enum import Enum


class ConstraintStrength(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def weight(self):
        return {self.LOW: 0.05, self.MEDIUM: 0.15, self.HIGH: 0.3}[self]
