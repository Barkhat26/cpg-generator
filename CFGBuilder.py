import logging
from typing import Dict, List

from antlr4 import *
from CFGVisitor import CFGVisitor
from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser
from db import Database
from graphs.cfg.ControlFlowGraph import ControlFlowGraph

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

class CFGBuilder:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.CFGs = dict()

    def getCFGs(self):
        return self.CFGs

    def build(self, filePath: str) -> Dict[str, ControlFlowGraph]:
        inputStream = FileStream(filePath)
        lexer = JavaLexer(inputStream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParser(tokens)
        parseTree = parser.compilationUnit()
        cfgs = dict()
        visitor = CFGVisitor(cfgs, filePath=filePath)
        visitor.visit(parseTree)

        for qn, CFG in cfgs.items():
            for v in CFG.nodes:
                v.setMethod(qn)

            CFG.setProperty("filePath", filePath)

        self.CFGs = cfgs

    def dump(self):
        db = Database(self.projectConfig)
        for qn, CFG in self.CFGs.items():
            db.putCFG(qn, CFG)
