import os.path
import networkx as nx
from networkx.drawing.nx_pydot import write_dot

from graphs.digraph import Digraph
from config import Config


class CallGraph(Digraph):
    def exportDot(self):
        G = nx.DiGraph()
        for n in self.nodes:
            G.add_node(n, shape="box")
        for e in self.allEdges:
            G.add_edge(e.source, e.target, label=e.label)
        write_dot(G, os.path.join(Config.PLOTS_DIR, "callgraph.dot"))