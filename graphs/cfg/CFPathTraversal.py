from graphs.cfg.CFNode import CFNode
from graphs.cfg.ControlFlowGraph import ControlFlowGraph
from utils import Queue


class CFPathTraversal:
    def __init__(self, cfg: ControlFlowGraph, startNode: CFNode):
        self.cfg = cfg
        self.startNode = startNode
        self.paths = Queue()
        self._continueNextPath = False
        self.current = None
        self.nextEdge = None

    def start(self):
        self.nextEdge = None
        self.current = self.startNode
        return self.current

    def hasNext(self):
        return self.current is None or \
            not self.paths.isEmpty() or \
            self.cfg.getOutDegree(self.current) > 0 and not self._continueNextPath

    def next(self):
        if self.current is None:
            return self.start()

        if not self._continueNextPath:
            for out in self.cfg.outEdges[self.current.Id]:
                self.paths.push(out)

        self._continueNextPath = False

        if self.paths.isEmpty():
            return None

        self.nextEdge = self.paths.pop()
        self.current = self.nextEdge.target
        return self.current

    def continueNextPath(self):
        self._continueNextPath = True