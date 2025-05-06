from pathlib import Path
from typing import Iterable
import networkx as nx

from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.cfg.cfg_edge import CFEdgeKind, CFEdge
from graphs.cfg.cfg_node import CFNodeKind, CFNode
from plots import CFGGraphVizExporter



class ControlFlowGraphNX:
    def __init__(self):
        self.g = nx.DiGraph()
        self.current_node_id = 0
        self._ast: AbstractSyntaxTreeNX | None = None
        self.properties = dict()
        self.entries: dict[str, CFNode] = dict()

    def attach_ast(self, ast: AbstractSyntaxTreeNX):
        self._ast = ast

    def get_entry(self, method_name: str) -> CFNode | None:
        # TODO: определять по qn
        result = [n for n in self.nodes if n.kind == CFNodeKind.ENTRY and n.get_optional_property('name') == method_name]

        if not result:
            return None

        assert len(result) == 1

        return result[0]

    @property
    def nodes(self) -> Iterable[CFNode]:
        for node_id, data in self.g.nodes(data=True):
            yield CFNode(node_id=node_id, **data)

    @property
    def edges(self) -> Iterable[CFEdge]:
        return [CFEdge(CFNode(node_id=s, **self.g.nodes[s]), data['kind'], CFNode(node_id=t, **self.g.nodes[t]))
                for s, t, data in self.g.edges(data=True)]

    def add_node(self, kind: CFNodeKind, line: int = 0, file: str | None = None, method: str | None = None, code: str = "", shared_id: str = None, optional_properties: dict[str, any] = None):
        self.current_node_id += 1
        self.g.add_node(self.current_node_id,
                        kind=kind,
                        line=line,
                        file=file,
                        method=method,
                        code=code,
                        shared_id=shared_id,
                        optional_properties=optional_properties
                        )
        return CFNode(
            node_id=self.current_node_id,
            kind=kind,
            line=line,
            file=file,
            method=method,
            code=code,
            shared_id=shared_id,
            optional_properties=optional_properties
        )

    def add_entry_node(self, method_qn: str, entry_node: CFNode):
        self.entries[method_qn] = entry_node

    # TODO: избавиться
    def update_node(self, new_node: CFNode):
        self.g.nodes[new_node.Id].update(dict(
            kind=new_node.kind,
            line=new_node.line,
            file=new_node.file,
            method=new_node.method,
            code=new_node.code,
            shared_id=new_node.shared_id,
            optional_properties=new_node.optional_properties,
        ))

    def add_edge(self, source: CFNode, target: CFNode, kind: CFEdgeKind = CFEdgeKind.EPS):
        self.g.add_edge(source.Id, target.Id, kind=kind)

    def out_nodes(self, node_id):
        if node_id not in self.g:
            return None

        return self.g[node_id]

    def in_nodes(self, node_id):
        if node_id not in self.g:
            return None

        return list(self.g.predecessors(node_id))

    def out_edges(self, node_id) -> list[CFEdge]:
        if node_id not in self.g:
            return []

        return [CFEdge(CFNode(node_id=s, **self.g.nodes[s]), data['kind'], CFNode(node_id=t,**self.g.nodes[t]))
                for s, t, data in self.g.out_edges(node_id, data=True)]

    def out_degree(self, node_id) -> int | None:
        if node_id not in self.g:
            return None

        return int(self.g.out_degree[node_id])

    def in_degree(self, node_id):
        if node_id not in self.g:
            return None

        return self.g.in_degree(node_id)

    def get_property(self, prop: str):
        return self.properties.get(prop)

    def set_property(self, prop: str, value: str):
        self.properties[prop] = value

    def get_node_by_shared_id(self, shared_id) -> CFNode | None:
        node = None
        for node_id, data in self.g.nodes(data=True):
            if data['shared_id'] == shared_id:
                node = CFNode(node_id=node_id, **data)
                break
        return node

    def export(self, dest_dir: Path | str = None):
        for qn, entry in self.entries.items():
            self.export_entry(qn, entry, dest_dir)

    def export_entry(self, qn: str, entry: CFNode, dest_dir: Path | str = None):
        component_nodes = next(
            c for c in nx.weakly_connected_components(self.g) if entry.Id in c
        )
        subgraph = self.g.subgraph(component_nodes).copy()
        CFGGraphVizExporter().export(subgraph, qn, dest_dir)
