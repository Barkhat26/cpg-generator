from graphs.ddg.dfg_node import DFNode
# from graphs.digraph import Edge
from enum import Enum, auto


class DFEdgeKind(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    INTRA = auto()
    INTER = auto()


class DFEdge:
    def __init__(self, source: DFNode, label: str, target: DFNode, kind: DFEdgeKind):
        self.source = source
        self.target = target
        self.label = label
        self.kind = kind
