from pathlib import Path
import networkx as nx

from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.ast.ast_node import ASNode
from plots import AbstractSyntaxGraphVizExporter


class AbstractSyntaxForest(AbstractSyntaxTreeNX):
    def __init__(self):
        super().__init__()
        self.roots: dict[str, ASNode] = dict()

    def export(self, dest_dir: Path | str = None):
        for filename, root in self.roots.items():
            self.export_root(filename, root, dest_dir)

    def export_root(self, qn: str, root: ASNode, dest_dir: Path | str = None):
        component_nodes = next(
            c for c in nx.weakly_connected_components(self.g) if root.Id in c
        )
        subgraph = self.g.subgraph(component_nodes).copy()
        AbstractSyntaxGraphVizExporter().export(subgraph, qn, dest_dir)
