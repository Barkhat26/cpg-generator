from typing import Dict
import pyorient
from db import Database
from graphs.ast import ASNode
from graphs.cfg.CFNode import CFNode
from graphs.ddg.DFEdge import DFEdgeKind
from graphs.ddg.DFNode import DFNode
import json

class ClassName:
    ASTNode = "ASTNode"
    ASTEdge = "ASTEdge"
    CFGNode = "CFGNode"
    CFGEdge = "CFGEdge"
    DFGNode = "DFGNode"
    DFGEdge = "DFGEdge"

class OrientDB:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.client = pyorient.OrientDB("localhost", 2424)
        self.client.db_open(
            self.projectConfig["orientdb-name"],
            self.projectConfig["orientdb-user"],
            self.projectConfig["orientdb-pass"]
        )
        self.checkStructure()

    def checkStructure(self):
        if not self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % ClassName.ASTNode):
            self.client.command("CREATE CLASS %s EXTENDS V" % ClassName.ASTNode)
        if not self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % ClassName.ASTEdge):
            self.client.command("CREATE CLASS %s EXTENDS E" % ClassName.ASTEdge)
        if not self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % ClassName.CFGNode):
            self.client.command("CREATE CLASS %s EXTENDS V" % ClassName.CFGNode)
        if not self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % ClassName.CFGEdge):
            self.client.command("CREATE CLASS %s EXTENDS E" % ClassName.CFGEdge)
        if not self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % ClassName.DFGNode):
            self.client.command("CREATE CLASS %s EXTENDS V" % ClassName.DFGNode)
        if not self.client.command("SELECT name FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % ClassName.DFGEdge):
            self.client.command("CREATE CLASS %s EXTENDS E" % ClassName.DFGEdge)

    def populate(self):
        self.populateASTs()
        self.populateCFGs()
        self.populateDFGs()

    def clear(self):
        self.client.command("DELETE VERTEX ASTNode")
        self.client.command("DELETE VERTEX CFGNode")
        self.client.command("DELETE VERTEX DFGNode")

    def populateASTs(self):
        print("Populating ASTs...")
        self.client.command("DELETE VERTEX ASTNode")
        ASTs = Database(self.projectConfig).getAllASTs()
        for name, AST in ASTs.items():
            for v in AST.nodes:
                ASTNodeRecord = {
                    "@ASTNode": self.serializeASTNode(v)
                }

                clusterId = self.getDefaultClusterId(ClassName.ASTNode)
                self.client.record_create(clusterId, ASTNodeRecord)

            for e in AST.allEdges:
                source = e.source.Id
                target = e.target.Id
                label = "ASTNode"
                self.client.command(f"CREATE EDGE ASTEdge FROM ( SELECT FROM ASTNode WHERE Id={source} and file='{name}' ) "
                                    f"TO ( SELECT FROM ASTNode WHERE Id={target} and file='{name}' ) "
                                    f"SET label='{label}'")

    def populateCFGs(self):
        print("Populating CFGs...")
        self.client.command("DELETE VERTEX CFGNode")
        CFGs = Database(self.projectConfig).getAllCFGs()
        for name, CFG in CFGs.items():
            for v in CFG.nodes:
                CFGNodeRecord = {
                    "@CFGNode": self.serializeCFGNode(v)
                }
                clusterId = self.getDefaultClusterId(ClassName.CFGNode)
                self.client.record_create(clusterId, CFGNodeRecord)

            for e in CFG.allEdges:
                source = e.source.Id
                target = e.target.Id
                label = e.label
                self.client.command(f"CREATE EDGE CFGEdge FROM ( SELECT FROM CFGNode WHERE Id={source} and method='{name}' ) "
                               f"TO ( SELECT FROM CFGNode WHERE Id={target} and method='{name}' ) "
                               f"SET label='{label}'")

    def populateDFGs(self):
        print("Populating DFGs...")
        self.client.command("DELETE VERTEX DFGNode")
        DFGs = Database(self.projectConfig).getAllDFGs()
        for name, DFG in DFGs.items():
            for v in DFG.nodes:
                DFGNodeRecord = {
                    "@DFGNode": self.serializeDFGNode(v)
                }
                clusterId = self.getDefaultClusterId(ClassName.DFGNode)
                self.client.record_create(clusterId, DFGNodeRecord)

        for name, DFG in DFGs.items():
            for e in DFG.allEdges:
                sourceId = e.source.Id
                targetId = e.target.Id
                label = e.label
                kind = e.kind.name
                if e.kind == DFEdgeKind.INTRA:
                    self.client.command(f"CREATE EDGE DFGEdge FROM ( SELECT FROM DFGNode WHERE Id={sourceId} and method='{name}' ) "
                                    f"TO ( SELECT FROM DFGNode WHERE Id={targetId} and method='{name}' ) "
                                    f"SET label='{label}', kind='{kind}'")
                else:
                    targetMethodName = e.target.method
                    self.client.command(
                        f"CREATE EDGE DFGEdge FROM ( SELECT FROM DFGNode WHERE Id={sourceId} and method='{name}' ) "
                        f"TO ( SELECT FROM DFGNode WHERE Id={targetId} and method='{targetMethodName}' ) "
                        f"SET label='{label}', kind='{kind}'")

    def serializeASTNode(self, node: ASNode) -> Dict[str, str]:
        serialized = {
            "Id": node.Id,
            "kind": node.kind.name,
            "line": node.line,
            "code": node.code,
            "sharedId": node.sharedId,
            "file": node.file,
            "optionalProperties": json.dumps(node.optionalProperties)
        }

        return serialized

    def serializeCFGNode(self, node: CFNode) -> Dict[str, str]:
        serialized = {
            "Id": node.Id,
            "kind": node.kind.name,
            "line": node.line,
            "code": node.code,
            "sharedId": node.sharedId,
            "method": node.method,
            "file": node.file,
            "optionalProperties": json.dumps(node.optionalProperties)
        }

        return serialized

    def serializeDFGNode(self, node: DFNode) -> Dict[str, str]:
        serialized = {
            "Id": node.Id,
            "line": node.line,
            "code": node.code,
            "sharedId": node.sharedId,
            "method": node.method,
            "file": node.file,
            "DEFs": node.DEFs,
            "USEs": node.USEs,
            "selfFlows": node.selfFlows,
            "IP_DEFs": node.IP_DEFs,
            "optionalProperties": json.dumps(node.optionalProperties)
        }

        return serialized

    def getDefaultClusterId(self, className: ClassName):
        oRecords = self.client.command(
            "SELECT defaultClusterId FROM (SELECT expand(classes) FROM metadata:schema) WHERE name='%s'" % className
        )
        oRecord = oRecords[0]
        oRecordData = oRecord.oRecordData
        return oRecordData["defaultClusterId"]

