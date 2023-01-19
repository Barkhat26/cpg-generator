from copy import copy
from typing import Set, Dict

from db import Database
from graphs.ast.ASNode import ASNodeKind
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cfg.CFEdge import CFEdge
from graphs.cfg.CFPathTraversal import CFPathTraversal
from graphs.cfg.ControlFlowGraph import ControlFlowGraph
from graphs.cpg.Call import Call
from graphs.ddg.DFEdge import DFEdgeKind
from graphs.ddg.DFNode import DFNode
from graphs.ddg.DataFlowGraph import DataFlowGraph
from graphs.digraph import Edge
from utils import Queue


class CodePropertyGraph:
    def __init__(self):
        self.ASTs = Database().getAllASTs()
        self.paths = []

    def calls(self, name=None):
        results = []
        for AST in self.ASTs.values():
            results += [Call(n, AST) for n in AST.nodes if n.kind == ASNodeKind.CALL]
        if name is not None:
            if "." not in name:
                results = [c for c in results if c.name == name]
            else:
                methodName = name.split(".")[-1]
                tmpResults = [c for c in results if c.name == methodName]
                finalResults = []
                for i in tmpResults:
                    qualifiedName = i.AST.putDotTogether(i.AST.getNodeByID(i.sharedId))
                    if qualifiedName == name:
                        i.name = qualifiedName
                        finalResults.append(i)
                results = finalResults
        return results

    def findDataFlowParent(self, call: Call):
        for dfg in Database().getAllDFGs().values():
            current = call.AST.getNodeByID(call.sharedId)
            while True:
                if len(call.AST.inEdges[current.Id]) == 0:
                    break

                # AST is not a multigraph, therefore self.ast.inEdges[current] set length is always 1 or 0 (root)
                parent = list(call.AST.inEdges[current.Id])[0].source
                if dfg.getNodeByID(parent.sharedId):
                    return dfg.getNodeByID(parent.sharedId), dfg
                current = parent

        return None, None

    def getDataFlowsForSource(self, dataFlowSource: DFNode) -> Set[Edge]:
        for dfg in self.dfgs.values():
            if dfg.outEdges.get(dataFlowSource.Id):
                return dfg.outEdges.get(dataFlowSource.Id)

    def findDataFlowTarget(self, dfnode: DFNode, call: Call):
        results = []
        for dataFlow in self.getDataFlowsForSource(dfnode):
            queue = Queue()
            dfTarget = dataFlow.target

            current = self.ast.getNodeByID(dfTarget.sharedId)
            queue.push(current)

            while not queue.isEmpty():
                current = queue.pop()

                if current.sharedId == call.sharedId:
                    results.append(current)
                    break

                for on in self.ast.outNodes(current):
                    queue.push(on)

        return results

    def getCFPathsForDataFlow(self, dfSource: DFNode, dfTarget: DFNode):
        CFSource, CFTarget = None, None

        for dfg in self.dfgs.values():
            if dfg.cfg.getNodeByID(dfSource.sharedId):
                CFSource = dfg.cfg.getNodeByID(dfSource.sharedId)
            if dfg.cfg.getNodeByID(dfTarget.sharedId):
                CFTarget = dfg.cfg.getNodeByID(dfTarget.sharedId)
        if CFSource is None or CFTarget is None:
            return None

        self.paths.clear()
        self.findAllPaths(CFSource, CFTarget)
        return self.paths

    def findAllPaths(self, source, target):
        visited = [False] * len(self.dfg.cfg.nodes)
        self.findAllPathsUtil(source, target, visited)

    def findAllPathsUtil(self, source, target, visited, path=None):
        # Пометить текущий узел как посещенный и сохранить в path
        if path is None:
            path = []
        visited[list(self.dfg.cfg.nodes).index(source)] = True
        path.append(source)

        # Если текущая вершина совпадает с точкой назначения, то
        # print(current path[])
        if source.sharedId == target.sharedId:
            self.paths.append(copy(path))
        else:
            # Если текущая вершина не является пунктом назначения
            # Повторить для всех вершин, смежных с этой вершиной
            for i in self.dfg.cfg.outNodes(source):
                if visited[list(self.dfg.cfg.nodes).index(i)] == False:
                    self.findAllPathsUtil(i, target, visited, path)

        # Удалить текущую вершину из path[] и пометить ее как непосещенную
        path.pop()
        visited[list(self.dfg.cfg.nodes).index(source)] = False

    def checkReachability(self, dfSource: DFNode, dfTarget: DFNode, sourceDFGName: str):
        sourceDFG = Database().getDFG(sourceDFGName)
        queue = Queue()
        queue.push(dfSource)

        while not queue.isEmpty():
            current = queue.pop()

            if current.getSharedId() == dfTarget.getSharedId():
                return True

            if current.IP_DEFs is not None:
                # newDFSource = [e for e in sourceDFG.outEdges[current.Id] if e.kind == DFEdgeKind.INTER][0].target
                # newSourceDFG = Database().getDFG(current.IP_DEFs["methodName"])
                newSourceDFGName = current.IP_DEFs["methodName"]
                newSourceDFG = Database().getDFG(newSourceDFGName)
                newDFSource = newSourceDFG.getEntry()
                if self.checkReachability(newDFSource, dfTarget, newSourceDFGName):
                    return True

            for edge in sourceDFG.outEdges[current.Id]:
                if edge.kind != DFEdgeKind.INTER:
                    queue.push(edge.target)

        return False

    def getCFSubgraph(self, dfSource, dfTarget):
        cfSource = self.dfg.cfg.getNodeByID(dfSource.sharedId)
        cfTarget = self.dfg.cfg.getNodeByID(dfTarget.sharedId)

        subgraph = ControlFlowGraph()

        visited = set()
        traversal = CFPathTraversal(self.dfg.cfg, cfSource)
        while traversal.hasNext():
            cfNode = traversal.next()
            if cfNode in visited:
                traversal.continueNextPath()
            else:
                subgraph.addVertex(cfNode)
                visited.add(cfNode)

                if cfNode.sharedId == cfTarget.sharedId:
                    traversal.continueNextPath()

        for cfNode in subgraph.nodes:
            # У начального узла нет предшественника
            if cfNode.sharedId == cfSource.sharedId:
                continue
            for edge in self.dfg.cfg.inEdges[cfNode]:
                subgraph.addEdge(edge)

        return subgraph

    def getInitialCFSubgraph(self, dfSourceSharedId: str):
        initialSubgraph = ControlFlowGraph()

        fullCFG = None
        cfSource = None
        for CFG in Database().getAllCFGs().values():
            if CFG.getNodeByID(dfSourceSharedId):
                fullCFG = CFG
                cfSource = CFG.getNodeByID(dfSourceSharedId)
                break

        traversal = CFPathTraversal(fullCFG, cfSource)
        visited = set()
        while traversal.hasNext():
            cfNode = traversal.next()
            if cfNode.Id in visited:
                traversal.continueNextPath()
            else:
                newCFNode = copy(cfNode)
                initialSubgraph.addVertex(newCFNode)
                visited.add(cfNode.Id)

        for i in range(1, initialSubgraph.size()):
            for edge in fullCFG.inEdges[i + cfSource.Id]:
                source = initialSubgraph.nodes[edge.source.Id - cfSource.Id]
                target = initialSubgraph.nodes[edge.target.Id - cfSource.Id]
                newCFEdge = CFEdge(source, edge.label, target)
                initialSubgraph.addEdge(newCFEdge)

        return initialSubgraph
