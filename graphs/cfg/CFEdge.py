from enum import Enum, auto


class CFEdgeKind(Enum):
    EPS = auto()
    TRUE = auto()
    FALSE = auto()
    THROWS = auto()


class CFEdge:
    def __init__(self, source, label, target):
        self.source = source
        self.label = label
        self.target = target

    def __eq__(self, other):
        if self.label != other.label:
            return False

        if self.source != other.source:
            return False

        if self.target != other.target:
            return False

        return True