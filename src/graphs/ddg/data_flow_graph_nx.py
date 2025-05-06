from pathlib import Path
from typing import Iterable
import networkx as nx

from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.cfg.cfg_node import CFNode
from graphs.cfg.control_flow_graph_nx import ControlFlowGraphNX
from graphs.ddg.dfg_edge import DFEdgeKind, DFEdge
from graphs.ddg.dfg_node import DFNode
from plots import DFGGraphVizExporter


class DataFlowGraphNX:
    def __init__(self):
        self.g = nx.DiGraph()
        self.current_node_id = 0
        self.ast: AbstractSyntaxTreeNX | None = None
        self.cfg: ControlFlowGraphNX | None = None
        self.properties = dict()

    @property
    def entry(self):
        return DFNode(node_id=1, **self.g.nodes[1])

    @property
    def nodes(self) -> Iterable[DFNode]:
        for node_id, data in self.g.nodes(data=True):
            yield DFNode(node_id=node_id, **data)

    @property
    def edges(self) -> Iterable[DFEdge]:
        return [DFEdge(DFNode(node_id=s, **self.g.nodes[s]), data['label'], DFNode(node_id=t, **self.g.nodes[t]), data['kind'])
                for s, t, data in self.g.edges(data=True)]

    def add_node(self, line: int = 0, file: str | None = None, method: str | None = None, code: str = "", shared_id: str = None, optional_properties: dict[str, any] = None,
                 defs: set[str] | None = None,
                 uses: set[str] | None = None,
                 self_flows: set[str] | None = None,
                 ip_defs=None):
        self.current_node_id += 1
        self.g.add_node(self.current_node_id,
                        line=line,
                        file=file,
                        method=method,
                        code=code,
                        shared_id=shared_id,
                        optional_properties=optional_properties,
                        defs=defs,
                        uses=uses,
                        self_flows=self_flows,
                        ip_defs=ip_defs
                        )
        return DFNode(
            node_id=self.current_node_id,
            line=line,
            file=file,
            method=method,
            code=code,
            shared_id=shared_id,
            optional_properties=optional_properties,
            defs=defs,
            uses=uses,
            self_flows=self_flows,
            ip_defs=ip_defs
        )

    # TODO: избавиться
    def update_node(self, new_node: DFNode):
        self.g.nodes[new_node.Id].update(dict(
            line=new_node.line,
            file=new_node.file,
            method=new_node.method,
            code=new_node.code,
            shared_id=new_node.shared_id,
            optional_properties=new_node.optional_properties,
            defs=new_node.defs,
            uses=new_node.uses,
            self_flows=new_node.self_flows,
            ip_defs=new_node.ip_defs
        ))

    def add_edge(self, source: DFNode, target: DFNode, label: str | None = None, kind: DFEdgeKind = DFEdgeKind.INTRA):
        self.g.add_edge(source.Id, target.Id, label=label, kind=kind)

    def out_nodes(self, node_id):
        if node_id not in self.g:
            return None

        return self.g[node_id]

    def in_nodes(self, node_id):
        if node_id not in self.g:
            return None

        return list(self.g.predecessors(node_id))

    def out_degree(self, node_id):
        if node_id not in self.g:
            return None

        return self.g.out_degree(node_id)

    def in_degree(self, node_id):
        if node_id not in self.g:
            return None

        return self.g.in_degree(node_id)

    def get_property(self, prop: str):
        return self.properties.get(prop)

    def set_property(self, prop: str, value: str):
        self.properties[prop] = value

    def get_node_by_id(self, node_id: int):
        return DFNode(node_id=node_id, **self.g.nodes[node_id])

    def get_node_by_shared_id(self, shared_id: str) -> DFNode | None:
        node = None
        for node_id, data in self.g.nodes(data=True):
            if data['shared_id'] == shared_id:
                node = DFNode(node_id=node_id, **data)
                break
        return node
    #
    # def export(self, filename="default"):
    #     dot = graphviz.Digraph()
    #     dot.format = "svg"
    #
    #     # Draw CFG nodes
    #     for cfg_node in self.cfg.nodes:
    #         # Make dot2svg to correctly handle html labels
    #         code = escapeForHtml(cfg_node.code)
    #         label = f'''<
    #         <table border="0" cellborder="0" cellspacing="1">
    #              <tr><td align="center">{code}</td></tr>
    #         </table>>'''
    #
    #         dot.node(
    #             str(cfg_node.Id),
    #             label=label,
    #             tooltip=str(cfg_node.Id) + ":" + str(cfg_node.shared_id),
    #             shape="box"
    #         )
    #
    #     # Draw CFG edges
    #     for cfg_edge in self.cfg.edges:
    #         dot.edge(str(cfg_edge.source.Id), str(cfg_edge.target.Id), label=cfg_edge.label.name, style="dashed", color="grey", fontcolor="grey")
    #
    #     # Draw DFG edges
    #     for dfg_edge in self.edges:
    #         # Inter-procedural data-flows are ignored
    #         if dfg_edge.kind == DFEdgeKind.INTER:
    #             continue
    #
    #         cfg_source = self.cfg.get_node_by_shared_id(dfg_edge.source.shared_id)
    #         cfg_target = self.cfg.get_node_by_shared_id(dfg_edge.target.shared_id)
    #
    #         dfg_color = "#239da8"
    #         dot.edge(str(cfg_source.Id), str(cfg_target.Id), label=dfg_edge.label, color=dfg_color, fontcolor=dfg_color)
    #
    #     dot.render(directory=Config.DFG_PLOTS_DIR, filename=f"dfg-{filename}", cleanup=True)

    def get_data_flow_parent(self, shared_id: str, ast: AbstractSyntaxTreeNX):
        current_ast_id = ast.get_node_by_shared_id(shared_id).Id

        while True:
            if len(ast.in_nodes(current_ast_id)) == 0:
                break

            # AST is not a multigraph, therefore self.ast.inEdges[current] set length is always 1 or 0 (root)
            ast_parent = ast.get_node_by_id(ast.in_nodes(current_ast_id)[0])

            if parent_df_node := self.get_node_by_shared_id(ast_parent.shared_id):
                return parent_df_node

            current_ast_id = ast_parent.Id

        return None

    def export(self, dest_dir: Path | str = None):
        for qn, cfg_entry in self.cfg.entries.items():
            self.export_entry(qn, cfg_entry, dest_dir)

    def export_entry(self, qn: str, cfg_entry: CFNode, dest_dir: Path | str = None):
        cfg_component_nodes = next(
            c for c in nx.weakly_connected_components(self.cfg.g) if cfg_entry.Id in c
        )
        cfg_subgraph = self.cfg.g.subgraph(cfg_component_nodes).copy()
        DFGGraphVizExporter(self.cfg, self.edges).export(cfg_subgraph, qn, dest_dir)