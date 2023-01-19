from graphs.cfg.CFEdge import CFEdgeKind
from graphs.cfg.CFNode import CFNode


class ControlFlowChain:
    def __init__(self):
        self.items = []
        self.edges = {}

    def addNode(self, newNode: CFNode, edgeKind: CFEdgeKind = None):
        self.items.append(newNode)
        self.edges[newNode] = edgeKind


