from graphs.cfg.cfg_edge import CFEdge
from graphs.cfg.cfg_node import CFNode
from graphs.cfg.control_flow_graph_nx import ControlFlowGraphNX
from utils.datatypes import Queue


class CFPathTraversal:
    def __init__(self, cfg: ControlFlowGraphNX, start_node: CFNode):
        self.cfg = cfg
        self.start_node = start_node
        self.paths = Queue(CFEdge)
        self._continue_next_path = False
        self.current: CFNode | None = None
        self.next_edge: CFEdge | None = None

    def start(self) -> CFNode:
        self.next_edge = None
        self.current = self.start_node
        return self.current

    def has_next(self) -> bool:
        return self.current is None or \
            not self.paths.isEmpty() or \
            self.cfg.out_degree(self.current.Id) > 0 and not self._continue_next_path

    def next(self) -> CFNode | None:
        if self.current is None:
            return self.start()

        if not self._continue_next_path:
            for out in self.cfg.out_edges(self.current.Id):
                self.paths.push(out)

        self._continue_next_path = False

        if self.paths.isEmpty():
            return None

        self.next_edge = self.paths.pop()
        self.current = self.next_edge.target
        return self.current

    def continue_next_path(self):
        self._continue_next_path = True
