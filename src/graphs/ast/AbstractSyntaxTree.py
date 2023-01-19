import subprocess
import graphviz

import networkx as nx
from antlr4 import ParserRuleContext
from networkx.drawing.nx_pydot import write_dot
import os.path
from typing import Optional

from graphs.ast.ASNode import ASNode, ASNodeKind
from graphs.digraph import Digraph

from config import Config


class AbstractSyntaxTree(Digraph):
    def __init__(self):
        super().__init__()
        self.properties = dict()
        root = ASNode(ASNodeKind.ROOT)
        self.addVertex(root)

    def getRoot(self):
        return self.nodes[0]

    def getNodeByCtx(self, ctx: ParserRuleContext) -> ASNode:
        from utils import getIdByCtx
        node = None
        for n in self.nodes:
            if n.sharedId == getIdByCtx(ctx):
                node = n
        return node

    def getNodeByID(self, _id) -> ASNode:
        node = None
        for n in self.nodes:
            if n.sharedId == _id:
                node = n
        return node

    def getParentOf(self, node: ASNode) -> Optional[ASNode]:
        inEdges = list(self.inEdges.get(node.Id))
        if inEdges:
            return inEdges[0].source
        else:
            return None  # node is a root

    def toNx(self):
        from utils import escapeForHtml
        G = nx.DiGraph()
        for idx, n in enumerate(self.nodes):
            if n.getCode() is None:
                label = n.kind.name
            else:
                code = n.getCode()
                # Make dot2svg to correctly handle html labels
                code = escapeForHtml(code)
                label = f'''<
<table border="0" cellborder="0" cellspacing="1">
     <tr><td align="left"><i><font color="#cc0000" point-size="9">{n.kind.name}</font></i></td></tr>
     <tr><td align="center">{code}</td></tr>
</table>>'''

            G.add_node(
                n,
                label=label,
                tooltip=str(n.getSharedId()),
                shape="box"
            )

        for edge in self.allEdges:
            G.add_edge(edge.source, edge.target, color="#008800")

        return G

    def exportDot(self, filename="default"):
        G = self.toNx()
        write_dot(G, os.path.join(Config.AST_PLOTS_DIR, f"ast-{filename}.dot"))

    def exportSVG(self, filename="default"):
        self.exportDot(filename)
        process = subprocess.Popen(
            ["bash", "-c", f"dot -Tsvg plots/AST/ast-{filename}.dot > plots/AST/ast-{filename}.svg"])

    def exportNew(self, filename="default"):
        from utils import escapeForHtml
        dot = graphviz.Digraph()
        dot.format = "svg"
        for idx, n in enumerate(self.nodes):
            if n.getCode() is None:
                label = n.kind.name
            else:
                code = n.getCode()
                # Make dot2svg to correctly handle html labels
                code = escapeForHtml(code)
                label = f'''<
        <table border="0" cellborder="0" cellspacing="1">
             <tr><td align="left"><i><font color="#cc0000" point-size="9">{n.kind.name}</font></i></td></tr>
             <tr><td align="center">{code}</td></tr>
        </table>>'''

            dot.node(
                str(n.Id),
                label=label,
                tooltip=str(n.Id) + ":" + str(n.getSharedId()),
                shape="box"
            )

        for edge in self.allEdges:
            dot.edge(str(edge.source.Id), str(edge.target.Id), color="#008800")
        dot.render(directory=Config.AST_PLOTS_DIR, filename=f"ast-{filename}")

    def exportGraphML(self, filename="default"):
        G = nx.DiGraph()
        for idx, n in enumerate(self.nodes):
            G.add_node(id(n), label=n.kind.name, code=str(n.getCode()), ctxId=str(n.sharedId))

        for edge in self.allEdges:
            G.add_edge(id(edge.source), id(edge.target))
        nx.write_graphml(G, os.path.join(Config.AST_GRAPHML_DIR, f"ast-{filename}.xml"))

    def getAllNodesByKind(self, kind: ASNodeKind):
        return [n for n in self.nodes if n.kind == kind]

    def putDotTogether(self, rightNode: ASNode) -> str:
        from utils import Stack
        dotString = ""
        mainDotNode = self.getParentOf(rightNode)

        stack = Stack()
        stack.push(mainDotNode)

        while not stack.isEmpty():
            current = stack.pop()

            # skip least right part. its name we will add after this loop
            if current.kind == ASNodeKind.CALL:
                continue

            if current.kind != ASNodeKind.DOT:
                dotString += "." + current.getCode()

            for on in list(self.outNodes(current))[::-1]:
                stack.push(on)

        for on in self.outNodes(rightNode):
            if on.kind == ASNodeKind.NAME:
                dotString += "." + on.getCode()
                break

        dotString = dotString[1:]  # delete redundant '.' at the beginning

        return dotString

    # def putDotTogetherFromBottom(self, node: ASNode) -> str:
    #     dotString = ""
    #
    #     currentNode = self.inNodes(node)[0]
    #     while self.inNodes(currentNode)[0] != ASNodeKind.DOT:


    def getAllMethods(self):
        methodNames = []
        for node in self.nodes:
            if node.kind == ASNodeKind.METHOD:
                for on in self.outNodes(node):
                    if on.kind == ASNodeKind.NAME:
                        methodNames.append(on.getCode())
        return methodNames

    def getProperty(self, prop: str):
        return self.properties.get(prop)

    def setProperty(self, prop: str, value: str):
        self.properties[prop] = value
