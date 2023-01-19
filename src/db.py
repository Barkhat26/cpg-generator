import os
from typing import List, Dict

import pickledb
from pymongo import MongoClient

from JavaStructures import JavaClass, JavaMethod
from config import Config
from graphs.ast.ASNode import ASNode
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cfg.CFNode import CFNode
from graphs.cfg.ControlFlowGraph import ControlFlowGraph
from graphs.ddg.DFNode import DFNode
from graphs.ddg.DataFlowGraph import DataFlowGraph
from schemas import ControlFlowGraphSchema, DataFlowGraphSchema, AbstractSyntaxTreeSchema, JavaClassSchema, \
    JavaMethodSchema, TaintFlowSchema


class DBCollections:
    ASTs = "asts"
    CFGs = "cfgs"
    DFGs = "dfgs"
    JavaClasses = "javaClasses"
    TaintFlows = "taintFlows"
    CallGraph = "callGraph"


class DatabaseMeta(type):
    _instance = None

    def __call__(self, projectConfig):
        if self._instance is None:
            self._instance = super().__call__(projectConfig)
        return self._instance


class Database(metaclass=DatabaseMeta):
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.db = pickledb.load(self.projectConfig["DB"], False)
        self.checkStructure()

    def commit(self):
        if not os.path.exists(self.projectConfig["DB"]):
            open(self.projectConfig["DB"], "tw").close()

        self.db.dump()

    def checkStructure(self):
        if not self.db.exists(DBCollections.ASTs):
            self.db.dcreate(DBCollections.ASTs)
        if not self.db.exists(DBCollections.DFGs):
            self.db.dcreate(DBCollections.DFGs)
        if not self.db.exists(DBCollections.CFGs):
            self.db.dcreate(DBCollections.CFGs)
        if not self.db.exists(DBCollections.JavaClasses):
            self.db.dcreate(DBCollections.JavaClasses)
        if not self.db.exists(DBCollections.TaintFlows):
            self.db.lcreate(DBCollections.TaintFlows)
        if not self.db.exists(DBCollections.CallGraph):
            self.db.dcreate(DBCollections.CallGraph)

    def clear(self, dbName=None):
        if dbName is None:
            self.db.deldb()
        else:
            self.db.rem(dbName)
        self.checkStructure()

    def putAST(self, filename: str, ast: AbstractSyntaxTree):
        self.db.dadd(DBCollections.ASTs, (filename, AbstractSyntaxTreeSchema().dump(ast)))

    def getAST(self, qualifiedName: str) -> AbstractSyntaxTree:
        schema = AbstractSyntaxTreeSchema()
        return schema.load(self.db.dget(DBCollections.ASTs, qualifiedName))

    def getASTByFilePath(self, filePath: str) -> AbstractSyntaxTree:
        for pkg, AST in self.db.dgetall(DBCollections.ASTs).items():
            if AST["properties"]["filePath"] == filePath:
                return AbstractSyntaxTreeSchema().load(AST)

    def getAllASTs(self) -> Dict[str, AbstractSyntaxTree]:
        schema = AbstractSyntaxTreeSchema()
        ASTs = self.db.get(DBCollections.ASTs)
        results = dict()
        for filename, AST in ASTs.items():
            results[filename] = schema.load(AST)
        return results

    def putCFG(self, qualifiedName: str, cfg: ControlFlowGraph):
        self.db.dadd(DBCollections.CFGs, (qualifiedName, ControlFlowGraphSchema().dump(cfg)))

    def getCFG(self, qualifiedName: str) -> ControlFlowGraph:
        if not self.db.dexists(DBCollections.CFGs, qualifiedName):
            return None

        CFG = self.db.dget(DBCollections.CFGs, qualifiedName)
        if CFG is not None:
            return ControlFlowGraphSchema().load(CFG)
        return None

    def getAllCFGs(self) -> Dict[str, ControlFlowGraph]:
        schema = ControlFlowGraphSchema()
        CFGs = self.db.get(DBCollections.CFGs)
        results = dict()
        for qn, CFG in CFGs.items():
            results[qn] = schema.load(CFG)
        return results

    def getCFGsByFilePath(self, filePath: str) -> Dict[str, ControlFlowGraph]:
        schema = ControlFlowGraphSchema()
        results = dict()
        for qn, CFG in self.db.dgetall(DBCollections.CFGs).items():
            if CFG["properties"]["filePath"] == filePath:
                results[qn] = schema.load(CFG)
        return results

    def putDFG(self, qualifiedName: str, dfg: DataFlowGraph):
        self.db.dadd(DBCollections.DFGs, (qualifiedName, DataFlowGraphSchema().dump(dfg)))

    def getDFG(self, qualifiedName: str) -> DataFlowGraph:
        DFG = self.db.dget(DBCollections.DFGs, qualifiedName)
        if DFG is not None:
            return DataFlowGraphSchema().load(DFG)
        return None

    def getAllDFGs(self) -> Dict[str, DataFlowGraph]:
        schema = DataFlowGraphSchema()
        DFGs = self.db.get(DBCollections.DFGs)
        results = dict()
        for qn, DFG in DFGs.items():
            results[qn] = schema.load(DFG)
        return results

    def putJavaClass(self, qualifiedName: str, javaClass: JavaClass):
        self.db.dadd(DBCollections.JavaClasses, (qualifiedName, JavaClassSchema().dump(javaClass)))

    def getJavaClass(self, qualifiedName: str) -> JavaClass:
        javaClass = self.db.dget(DBCollections.JavaClasses, qualifiedName)
        if javaClass is not None:
            return JavaClassSchema().load(javaClass)

    def getJavaClassByName(self, name: str) -> JavaClass:
        for jc in self.db.get(DBCollections.JavaClasses):
            if jc["properties"]["name"] == name:
                return JavaClassSchema().load(jc)

        return None

    def getAllJavaClasses(self) -> Dict[str, JavaClass]:
        schema = JavaClassSchema()
        results = dict()
        for qn, jc in self.db.get(DBCollections.JavaClasses).items():
            results[qn] = schema.load(jc)
        return results

    def getAllMethods(self) -> Dict[str, JavaMethod]:
        methods = dict()
        for jc in self.getAllJavaClasses():
            for mtd in jc.methods:
                methods[mtd.name] = mtd
        return methods

    def getMethod(self, qualifiedClassName: str, methodName: str):
        cls = self.getJavaClass(qualifiedClassName)
        for method in cls.methods:
            if method.name == methodName:
                return method

    def getAllTaintFlows(self):
        schema = TaintFlowSchema()
        results = list()
        for tf in self.db.get(DBCollections.TaintFlows):
            results.append(schema.load(tf))
        return results

    def putTaintFlow(self, taintFlow):
        self.db.ladd(DBCollections.TaintFlows, TaintFlowSchema().dump(taintFlow))

    def setAllTaintFlows(self, taintFlowList):
        self.db.set(DBCollections.TaintFlows, TaintFlowSchema(many=True).dump(taintFlowList))

    def putInCallGraph(self, methodQN, callees):
        self.db.dadd(DBCollections.CallGraph, (methodQN, callees))

    def getCallGraphMethods(self):
        return self.db.get(DBCollections.CallGraph).keys()

    def getCallees(self, methodQN):
        return self.db.dget(DBCollections.CallGraph, methodQN)

    def getASTNodeBySharedId(self, sharedId: str) -> ASNode:
        for AST in self.getAllASTs().values():
            for node in AST.nodes:
                if node.getSharedId() == sharedId:
                    return node

        return None

    def getCFGNodeBySharedId(self, sharedId: str) -> CFNode:
        for CFG in self.getAllCFGs().values():
            for node in CFG.nodes:
                if node.getSharedId() == sharedId:
                    return node

        return None

    def getDFGNodeBySharedId(self, sharedId: str) -> DFNode:
        for DFG in self.getAllDFGs().values():
            for node in DFG.nodes:
                if node.getSharedId() == sharedId:
                    return node

        return None
