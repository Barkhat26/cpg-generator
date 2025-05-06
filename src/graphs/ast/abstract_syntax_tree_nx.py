import os
from pathlib import Path
import networkx as nx
from typing import Iterable

from graphs.ast.ast_edge import ASEdge
from graphs.ast.ast_node import ASNode, ASNodeKind
from plots import AbstractSyntaxGraphVizExporter
from optional_properties import OptionalProperties
from utils.datatypes import Stack


class AbstractSyntaxTreeNX:
    def __init__(self):
        self.g = nx.DiGraph()
        self.current_node_id = 0
        self.properties = dict()

    @property
    def nodes(self) -> Iterable[ASNode]:
        for node_id, data in self.g.nodes(data=True):
            yield ASNode(node_id=node_id, **data)

    @property
    def edges(self) -> Iterable[ASEdge]:
        return [ASEdge(ASNode(node_id=s, **self.g.nodes[s]), ASNode(node_id=t, **self.g.nodes[t]), data['label'])
                for s, t, data in self.g.edges(data=True)]

    @property
    def root(self) -> ASNode:
        return ASNode(node_id=1, **self.g.nodes[1])

    def add_node(self, kind: ASNodeKind, file=None, line: int = 0, code: str = "", shared_id: str = None, optional_properties: dict[str, any] = None) -> ASNode:
        self.current_node_id += 1
        self.g.add_node(self.current_node_id,
            kind=kind,
            file=file,
            line=line,
            code=code,
            shared_id=shared_id,
            optional_properties=optional_properties
        )
        return ASNode(
            node_id=self.current_node_id,
            kind=kind,
            file=file,
            line=line,
            code=code,
            shared_id=shared_id,
            optional_properties=optional_properties
        )

        # TODO: избавиться
    def update_node(self, new_node: ASNode):
        self.g.nodes[new_node.Id].update(dict(
            kind=new_node.kind,
            line=new_node.line,
            file=new_node.file,
            code=new_node.code,
            shared_id=new_node.shared_id,
            optional_properties=new_node.optional_properties,
        ))

    def get_node_by_id(self, node_id) -> ASNode:
        return ASNode(node_id=node_id, **self.g.nodes[node_id])

    def add_edge(self, source: ASNode, target: ASNode, label: str | None = None):
        self.g.add_edge(source.Id, target.Id, label=label)

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

    def get_node_by_shared_id(self, shared_id) -> ASNode:
        node = None
        for node_id, data in self.g.nodes(data=True):
            if data['shared_id'] == shared_id:
                node = ASNode(node_id=node_id, **data)
                break
        return node

    def put_dot_together(self, right_node: ASNode) -> str:
        dot_string = ""
        main_dot_node = self.in_nodes(right_node.Id)[0]

        stack = Stack(str)
        stack.push(main_dot_node)

        while not stack.isEmpty():
            current_id = stack.pop()
            current_ast_node = ASNode(node_id=current_id, **self.g.nodes[current_id])

            # skip the least right part. its name we will add after this loop
            if current_ast_node.kind == ASNodeKind.CALL:
                continue

            if current_ast_node.kind != ASNodeKind.DOT:
                dot_string += "." + current_ast_node.code

            for on in list(self.out_nodes(current_id))[::-1]:
                stack.push(on)

        for on in self.out_nodes(right_node.Id):
            on_ast_node = ASNode(node_id=on, **self.g.nodes[on])
            if on_ast_node.kind == ASNodeKind.NAME:
                dot_string += "." + on_ast_node.code
                break

        dot_string = dot_string[1:]  # delete redundant '.' at the beginning

        return dot_string

    def export(self, dest_dir: Path | str = None):
        # TODO: передавать осмысленное filename
        filepath = self.get_property(OptionalProperties.FilePath)
        qn = os.path.basename(os.path.splitext(filepath)[0]) if filepath  else "None"
        AbstractSyntaxGraphVizExporter().export(self.g, qn, dest_dir)