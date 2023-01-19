import subprocess

import graphviz
import networkx as nx
from antlr4 import ParserRuleContext
from networkx.drawing.nx_pydot import write_dot
import os.path

from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cfg.CFNode import CFNodeKind, CFNode

from graphs.digraph import Digraph
from config import Config


class ControlFlowGraph(Digraph):
    def __init__(self):
        super().__init__()
        self.ast: AbstractSyntaxTree = None
        self.properties = dict()

    def getProperty(self, prop: str):
        return self.properties.get(prop)

    def setProperty(self, prop: str, value: str):
        self.properties[prop] = value

    def getEntry(self):
        return self.nodes[0]

    def attachAST(self, ast: AbstractSyntaxTree):
        self.ast = ast

    def getNodeByCtx(self, ctx: ParserRuleContext) -> CFNode:
        from utils import getIdByCtx
        node = None
        for n in self.nodes:
            if n.sharedId == getIdByCtx(ctx):
                node = n
        return node

    def getNodeByID(self, _id):
        node = None
        for n in self.nodes:
            if n.sharedId == _id:
                node = n
        return node

    def toNx(self):
        from utils import escapeForHtml
        G = nx.DiGraph()
        for idx, n in enumerate(self.nodes):
            code = n.getCode()
            # Make dot2svg to correctly handle html labels
            code = escapeForHtml(code)

            label = f'''<
<table border="0" cellborder="0" cellspacing="1">
     <tr><td align="left"><i><font color="#cc0000" point-size="9">{n.kind.name}</font></i></td></tr>
     <tr><td align="center">{code}</td></tr>
</table>>'''

            G.add_node(
                n.Id,
                label=label,
                tooltip=n.getSharedId(),
                shape="box"
            )

        for edge in self.allEdges:
            G.add_edge(edge.source.Id, edge.target.Id, label=edge.label.name)

        return G

    def exportDot(self, filename="default"):
        G = self.toNx()
        write_dot(G, os.path.join(Config.CFG_PLOTS_DIR, f"cfg-{filename}.dot"))

    def exportSVG(self, filename="default"):
        self.exportDot(filename)
        process = subprocess.Popen(["bash", "-c", f"dot -Tsvg plots/CFG/cfg-{filename}.dot > plots/CFG/cfg-{filename}.svg"])

    def exportNew(self, filename="default"):
        from utils import escapeForHtml
        dot = graphviz.Digraph()
        dot.format = "svg"
        for idx, n in enumerate(self.nodes):
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
            dot.edge(str(edge.source.Id), str(edge.target.Id), label=edge.label.name)

        dot.render(directory=Config.CFG_PLOTS_DIR, filename=f"cfg-{filename}")

    def exportGraphML(self, filename="default"):
        G = nx.DiGraph()
        for idx, n in enumerate(self.nodes):
            G.add_node(id(n), label=n.kind.name, code=str(n.getCode()), ctxId=str(n.sharedId))

        for edge in self.allEdges:
            G.add_edge(id(edge.source), id(edge.target))
        nx.write_graphml(G, os.path.join(Config.CFG_GRAPHML_DIR, f"cfg-{filename}.xml"))


    def getAllNodesByKind(self, kind: CFNodeKind):
        return [n for n in self.nodes if n.kind == kind]

    def getMethodsToCFG(self):
        from graphs.cfg.CFPathTraversal import CFPathTraversal
        methodsToCFG = dict()
        for entry in self.getAllMethodEntries():
            cfSubgraph = ControlFlowGraph()
            traversal = CFPathTraversal(self, entry)
            visited = set()
            while traversal.hasNext():
                cfNode = traversal.next()

                if cfNode in visited:
                    traversal.continueNextPath()

                cfSubgraph.addVertex(cfNode)
                visited.add(cfNode)

            for node in cfSubgraph.nodes:
                for e in self.allEdges:
                    if e.target == node or e.source == node:
                        cfSubgraph.addEdge(e)

            methodsToCFG[entry.getProperty("name")] = cfSubgraph
        return methodsToCFG

    def __eq__(self, other):
        if len(self.nodes) != len(other.nodes):
            return False

        for i in range(len(self.nodes)):
            if self.nodes[i] != other.nodes[i]:
                return False

        if len(self.allEdges) != len(other.allEdges):
            return False

        for i in range(len(self.allEdges)):
            if self.allEdges[i] != other.allEdges[i]:
                return False
        
        if self.inEdges.keys() != other.inEdges.keys():
            return False
        
        for k in self.inEdges:
            if self.inEdges[k] != other.inEdges[k]:
                return False

        if self.outEdges.keys() != other.outEdges.keys():
            return False

        for k in self.outEdges:
            if self.outEdges[k] != other.outEdges[k]:
                return False

        return True
