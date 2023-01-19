import logging
from typing import List, Dict

from antlr4 import *
from DFGVisitor import DFGVisitor
from GremlinDriver import Gremlin
from JavaClassExtractor import JavaClassExtractor
from JavaStructures import MethodDefInfo
from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser
from db import Database
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cfg.CFPathTraversal import CFPathTraversal
from graphs.cfg.ControlFlowGraph import ControlFlowGraph
from graphs.ddg.DFEdge import DFEdge, DFEdgeKind
from graphs.ddg.DataFlowGraph import DataFlowGraph
from graphs.digraph import Edge

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


class DFGBuilder:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.DFGs = dict()

    def getDFGs(self):
        return self.DFGs

    def build(self, filePath: str, ast: AbstractSyntaxTree) -> Dict[str, DataFlowGraph]:
        inputStream = FileStream(filePath)
        lexer = JavaLexer(inputStream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParser(tokens)
        parseTree = parser.compilationUnit()

        # Extract the information of all given Java classes
        # logger.info("\nExtracting class-infos ... ")
        # classesList = JavaClassExtractor.extractInfo(filename, parseTree)
        # allClassInfos = dict()
        # for cls in classesList:
        #     allClassInfos[cls.name] = cls
        # logger.info("Done.")

        # Initialize method DEF information
        # logger.info("\nInitializing method-DEF infos ... ")
        # methodDEFs = dict()
        # for cls in classesList:
        #     for mtd in cls.methods:
        #         lst = methodDEFs.get(mtd.name)
        #         if lst is None:
        #             lst = []
        #             lst.append(MethodDefInfo(mtd.retType, mtd.name, cls.package, cls.name, mtd.args, mtd.sharedId))
        #             methodDEFs[mtd.name] = lst
        #         else:
        #             lst.append(MethodDefInfo(mtd.retType, mtd.name, cls.package, cls.name, mtd.args, mtd.sharedId))
        # logger.info("Done.")

        # Analyze method DEF information for imported libraries
        # TODO implement
        pass

        logger.info("Iterative DEF-USE analysis ... ")
        dfgs = dict()
        iteration = 0
        while True:
            iteration += 1
            changed = False
            visitor = DFGVisitor(iteration, dfgs, ast, filePath, Database(self.projectConfig), self.projectConfig)
            visitor.visit(parseTree)
            changed |= visitor.changed
            logger.debug("Iteration #" + str(iteration) + ": " + ("CHANGED" if changed else "NO-CHANGE"))
            logging.debug("========================================")
            if not changed:
                break
        logger.info("Done.")

        db = Database(self.projectConfig)
        for qn, dfg in dfgs.items():
            cfg = db.getCFG(qn)
            dfg.attachCFG(cfg)

        logger.info("Adding data-flows...")
        DFGBuilder.addDataFlowEdges(dfgs)

        for qn, dfg in dfgs.items():
            for v in dfg.nodes:
                v.setMethod(qn)

            dfg.setProperty("filePath", filePath)

        self.DFGs = dfgs

    @staticmethod
    def addDataFlowEdges(ddgs: Dict[str, DataFlowGraph]):
        visitedDefs = set()
        for qn, ddg in ddgs.items():
            cfg = ddg.getCFG()
            logger.info(f"Handling {qn} CFG...")
            visitedDefs.clear()
            entry = cfg.getEntry()
            defTraversal = CFPathTraversal(cfg, entry)
            while defTraversal.hasNext():
                defCFNode = defTraversal.next()

                if defCFNode.Id in visitedDefs:
                    defTraversal.continueNextPath()
                    continue
                visitedDefs.add(defCFNode.Id)

                defDDNode = ddg.getNodeByID(defCFNode.getSharedId())
                if defDDNode is None:
                    continue

                if len(defDDNode.getAllDEFs()) == 0 and not defDDNode.containsIPDEFs():
                    continue

                # first add any self-flows of this node
                for flow in defDDNode.getAllSelfFlows():
                    ddg.addEdge(Edge(defDDNode, flow, defDDNode))


                # now traverse the CFG for any USEs till a DEF
                visitedUses = set()
                for DEF in defDDNode.getAllDEFs():
                    useTraversal = CFPathTraversal(cfg, defCFNode)
                    visitedUses.clear()
                    useCFNode = useTraversal.next()
                    visitedUses.add(useCFNode.Id)
                    while useTraversal.hasNext():
                        useCFNode = useTraversal.next()
                        useDDNode = ddg.getNodeByID(useCFNode.getSharedId())
                        if useDDNode is None:
                            continue
                        if useDDNode.hasDEF(DEF):
                            useTraversal.continueNextPath()  # no need to continue this path
                        if useCFNode.Id in visitedUses:
                            useTraversal.continueNextPath()  # no need to continue this path
                        else:
                            visitedUses.add(useCFNode.Id)
                            if useDDNode.hasUSE(DEF):
                                ddg.addEdge(DFEdge(defDDNode, DEF, useDDNode, DFEdgeKind.INTRA))

    @staticmethod
    def addIPDataFlows(ddgs: Dict[str, DataFlowGraph], projectConfig):
        db = Database(projectConfig)
        for qn, ddg in ddgs.items():
            for node in ddg.nodes:
                if node.IP_DEFs is not None:
                    IPDFTarget = db.getDFGNodeBySharedId(node.IP_DEFs["entrySharedId"])
                    ddg.addEdge(DFEdge(
                        node, "inter-procedural", IPDFTarget, DFEdgeKind.INTER)
                    )
            db.putDFG(qn, ddg)

    def dump(self):
        db = Database(self.projectConfig)
        for qn, dfg in self.DFGs.items():
            db.putDFG(qn, dfg)