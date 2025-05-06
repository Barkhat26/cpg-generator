from graphs.cfg.cfg_edge import CFEdgeKind
from graphs.cfg.cfg_node import CFNode


class ControlFlowChain:
    def __init__(self):
        self.items = []
        self.edges = {}

    def addNode(self, newNode: CFNode, edgeKind: CFEdgeKind = None):
        self.items.append(newNode)
        self.edges[newNode] = edgeKind


