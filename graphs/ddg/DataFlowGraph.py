import logging
import subprocess

import graphviz
from antlr4 import ParserRuleContext
import networkx as nx
from networkx.drawing.nx_pydot import write_dot
import os.path

from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cfg.ControlFlowGraph import ControlFlowGraph
from graphs.ddg.DFEdge import DFEdgeKind, DFEdge
from graphs.ddg.DFNode import DFNode
from graphs.digraph import Digraph
from config import Config


class DataFlowGraph(Digraph):
    def __init__(self):
        super().__init__()
        self.cfg: ControlFlowGraph = None
        self.ast: AbstractSyntaxTree = None
        self.properties = dict()

    def getEntry(self):
        return self.nodes[0]

    # Если межпроцедурный поток данных, то в inEdges ничего не добавляем
    def addEdge(self, e: DFEdge):
        if e not in self.allEdges:
            self.allEdges.append(e)
            if e.kind == DFEdgeKind.INTRA:
                self.inEdges.get(e.target.Id).append(e)
            self.outEdges.get(e.source.Id).append(e)

    def getNodeByCtx(self, ctx: ParserRuleContext) -> DFNode:
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

    def attachCFG(self, cfg: ControlFlowGraph) -> None:
        self.cfg = cfg

    def attachAST(self, ast: AbstractSyntaxTree) -> None:
        self.ast = ast

    def getCFG(self):
        return self.cfg

    def printAllNodesUseDefs(self):
        for node in self.nodes:
            logging.info(node)
            logging.info(" + USEs: " + " ".join(node.getAllUSEs()))
            logging.info(" + DEFs: " + " ".join(node.getAllDEFs()))

    def toNx(self):
        from utils import escapeForHtml
        G = nx.MultiDiGraph()
        for idx, n in enumerate(self.cfg.nodes):
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
                tooltip=str(n.getSharedId()),
                shape="box"
            )

        # Add control-flow edges
        for edge in self.cfg.allEdges:
            G.add_edge(edge.source.Id, edge.target.Id, label=edge.label.name, style="dashed", color="grey")

        # Add data-flow edges
        for edge in self.allEdges:
            # Отображать межпроцедурные потоки данных пока не надо
            if edge.kind == DFEdgeKind.INTER:
                continue
            source = self.cfg.getNodeByID(edge.source.sharedId)
            target = self.cfg.getNodeByID(edge.target.sharedId)
            G.add_edge(source.Id, target.Id, label=edge.label, color="#239da8", fontcolor="#239da8")

        return G

    def exportDot(self, filename="default"):
        G = self.toNx()
        write_dot(G, os.path.join(Config.DFG_PLOTS_DIR, f"dfg-{filename}.dot"))

    def exportSVG(self, filename="default"):
        self.exportDot(filename)
        process = subprocess.Popen(["bash", "-c",
                                    f"dot -Tsvg plots/DFG/dfg-{filename}.dot > plots/DFG/dfg-{filename}.svg"])

    def exportNew(self, filename="default"):
        from utils import escapeForHtml
        dot = graphviz.Digraph()
        dot.format = "svg"
        for idx, n in enumerate(self.cfg.nodes):
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

        # Add control-flow edges
        for edge in self.cfg.allEdges:
            dot.edge(str(edge.source.Id), str(edge.target.Id), label=edge.label.name, style="dashed", color="grey")

        # Add data-flow edges
        for edge in self.allEdges:
            # Отображать межпроцедурные потоки данных пока не надо
            if edge.kind == DFEdgeKind.INTER:
                continue
            source = self.cfg.getNodeByID(edge.source.sharedId)
            target = self.cfg.getNodeByID(edge.target.sharedId)
            dot.edge(str(source.Id), str(target.Id), label=edge.label, color="#239da8", fontcolor="#239da8")
        dot.render(directory=Config.DFG_PLOTS_DIR, filename=f"dfg-{filename}")

    def getProperty(self, prop: str):
        return self.properties.get(prop)

    def setProperty(self, prop: str, value: str):
        self.properties[prop] = value
