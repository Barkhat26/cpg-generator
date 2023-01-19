from graphs.ddg.DFNode import DFNode
from graphs.digraph import Edge
from enum import Enum, auto


class DFEdgeKind(Enum):
    INTRA = auto()
    INTER = auto()


class DFEdge(Edge):
    def __init__(self, source: DFNode, label: str, target: DFNode, kind: DFEdgeKind):
        super().__init__(source, label, target)
        self.kind = kind
