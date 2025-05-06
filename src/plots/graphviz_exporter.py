from abc import abstractmethod, ABC
from pathlib import Path
import graphviz
from networkx.classes import Graph

from config import Config
from graphs.ast.ast_node import ASNodeKind
from graphs.cfg.cfg_node import CFNodeKind
from utils.other import escapeForHtml

NodeKind = (
    ASNodeKind,
    CFNodeKind,
)


class ExporterBase(ABC):
    @staticmethod
    @abstractmethod
    def get_filename_prefix() -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_edge_color(kind) -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_sub_dest_dir() -> Path | str:
        ...

    def export(self, g: Graph, filename: str, dest_dir: Path | str = None):
        dot = graphviz.Digraph()
        self.add_nodes_to_graphviz(g, dot)
        self.add_edges_to_graphviz(g, dot)
        _dest_dir = (Path(dest_dir) if dest_dir else Path(Config.DEFAULT_PLOTS_DIR)) / self.get_sub_dest_dir()
        dot.render(
            directory=_dest_dir,
            filename=f"{self.get_filename_prefix()}-{filename}",
            cleanup=True,
            format="svg"
        )

    @staticmethod
    def add_nodes_to_graphviz(g: Graph, dot: graphviz.Digraph):
        for n_id, n_data in g.nodes(data=True):
            if n_data['code'] is None:
                label = n_data['kind'].name
            else:
                label = ExporterBase._generate_label_from_template(n_data['code'], n_data['kind'])

            dot.node(
                str(n_id),
                label=label,
                tooltip=str(n_id) + ":" + str(n_data['shared_id']),
                shape="box"
            )

    def add_edges_to_graphviz(self, g: Graph, dot: graphviz.Digraph):
        for source_id, target_id, edge_data in g.edges(data=True):
            dot.edge(
                str(source_id),
                str(target_id),
                **self.get_additional_edge_attrs(edge_data)
            )

    @staticmethod
    def get_additional_edge_attrs(edge_data: dict) -> dict:
        return {}

    @staticmethod
    def _generate_label_from_template(code: str, kind: NodeKind):
        # Make dot2svg to correctly handle html labels
        code = escapeForHtml(code)
        return f'''<
                    <table border="0" cellborder="0" cellspacing="1">
                         <tr><td align="left"><i><font color="#cc0000" point-size="9">{kind.name}</font></i></td></tr>
                         <tr><td align="center">{code}</td></tr>
                    </table>>'''
