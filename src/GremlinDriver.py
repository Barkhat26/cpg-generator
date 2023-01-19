from gremlin_python import statics
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.strategies import *
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.traversal import T
from gremlin_python.process.traversal import Order
from gremlin_python.process.traversal import Cardinality
from gremlin_python.process.traversal import Column
from gremlin_python.process.traversal import Direction
from gremlin_python.process.traversal import Operator
from gremlin_python.process.traversal import P
from gremlin_python.process.traversal import Pop
from gremlin_python.process.traversal import Scope
from gremlin_python.process.traversal import Barrier
from gremlin_python.process.traversal import Bindings
from gremlin_python.process.traversal import WithOptions
import os
import json
from config import Config
from db import Database
from graphs.ast.ASNode import ASNode, ASNodeKind
from graphs.cfg.CFNode import CFNode, CFNodeKind
from graphs.ddg.DFNode import DFNode
from utils import preToInfix


class GremlinMeta(type):
    _instance = None

    def __call__(self, projectConfig):
        if self._instance is None:
            self._instance = super().__call__(projectConfig)
        return self._instance


class Gremlin(metaclass=GremlinMeta):
    def __init__(self, projectConfig):
        gremlinName = projectConfig["gremlin-name"]
        self.g = traversal().withRemote(DriverRemoteConnection('ws://localhost:8182/gremlin', gremlinName))

    def clear(self):
        self.g.V().drop().iterate()

    def getAllMethodNames(self):
        return self.g.V().has("label", "METHOD").out().has("label", "NAME").values("code").toList()

    # def getAllCallsInMethod(self, methodName):
    #     selectedG = None
    #     for filename in Database().getAllASTs().keys():
    #         self.clear()
    #         self.g.io(os.path.join(Config.AST_GRAPHML_DIR, f"ast-{filename}.xml")).read().iterate()
    #         if self.g.V().has("label", "METHOD").count().next() != 0:
    #             selectedG = self.g
    #             break
    #
    #     if selectedG is None:
    #         return
    #
    #     return selectedG.V().has("label", "METHOD").out().has("label", "NAME").has("code", methodName).inE().outV().emit() \
    #         .repeat(__.out()).has("label", "CALL").out().has("label", "NAME").values("code").toList()
    #
    # def getNodeBySharedId(self, sharedId):
    #     selectedG = None
    #     for filename in Database().getAllASTs().keys():
    #         self.clear()
    #         self.g.io(os.path.join(Config.AST_GRAPHML_DIR, f"ast-{filename}.xml")).read().iterate()
    #         if self.g.V().has("ctxId", sharedId).count().next() != 0:
    #             selectedG = self.g
    #             break
    #
    #     if selectedG is None:
    #         return
    #
    #     return selectedG.V().has("ctxId", sharedId).next()
    #
    # def getArgListForCall(self, sharedId):
    #     selectedG = None
    #     for filename in Database().getAllASTs().keys():
    #         self.clear()
    #         self.g.io(os.path.join(Config.AST_GRAPHML_DIR, f"ast-{filename}.xml")).read().iterate()
    #         if self.g.V().has("ctxId", sharedId).count().next() != 0:
    #             selectedG = self.g
    #             break
    #
    #     if selectedG is None:
    #         return
    #
    #     callNode = selectedG.V().has("ctxId", sharedId).next()
    #
    #     if selectedG.V(callNode).out().has("label", "PARAMS").count().next() == 0:
    #         return None
    #     else:
    #         paramsNode = selectedG.V(callNode).out().has("label", "PARAMS").next()
    #
    #     params = selectedG.V(paramsNode).out().toList()
    #     results = []
    #     for param in params:
    #         prefixList = selectedG.V(param).emit().repeat(__.out()).values("code").toList()
    #         results.append(preToInfix(prefixList))
    #     return results
    #
    # def getCallSharedId(self, parentSharedId: str):
    #     selectedG = None
    #     for filename in Database().getAllASTs().keys():
    #         self.clear()
    #         self.g.io(os.path.join(Config.AST_GRAPHML_DIR, f"ast-{filename}.xml")).read().iterate()
    #         if self.g.V().has("ctxId", parentSharedId).count().next() != 0:
    #             selectedG = self.g
    #             break
    #
    #     if selectedG is None:
    #         return
    #
    #     callNodeSharedId = selectedG.V().has("ctxId", parentSharedId).\
    #                                      repeat(__.out()).until(__.has("label", "CALL")).\
    #                                      values("ctxId").next()
    #
    #     return callNodeSharedId
    #
    # def isCallWithDot(self, callShareId: str):
    #     g = self.getASTByNodeSharedId(callShareId)
    #     callVertex = g.V().has("ctxId", callShareId).next()
    #     return g.V(callVertex).inE().outV().has("label", "DOT").count().next() != 0
    #
    # def getMainDotVertex(self, callShareId: str):
    #     g = self.getASTByNodeSharedId(callShareId)
    #     callVertex = g.V().has("ctxId", callShareId).next()
    #     return g.V(callVertex).repeat(__.inE().outV()).until(
    #         __.has("label", P.neq("DOT"))).out().has("label", "DOT").next()
    #
    # def putDotTogether(self, callShareId: str):
    #     mainDotVertex = self.getMainDotVertex(callShareId)
    #     results = self.g.V(mainDotVertex).repeat(__.out()).until(__.has("label", "PARAMS")).emit()\
    #                            .where(__.values("code").is_(P.neq("None")))\
    #                            .values("code").toList()
    #     return '.'.join(results)

    def getASTNodeBySharedId(self, sharedId: str):
        gremlinResp = self.g.V().hasLabel("ASTNode").has("sharedId", sharedId).valueMap().toList()

        if len(gremlinResp) == 0:
            return
        else:
            gremlinResp = gremlinResp[0]

        node = ASNode(ASNodeKind[gremlinResp["kind"][0]])
        node.Id = gremlinResp["Id"][0]
        node.sharedId = gremlinResp["sharedId"][0]
        node.setLineOfCode(gremlinResp["line"][0])
        node.setCode(gremlinResp["code"][0])
        return node

    def getCFGNodeBySharedId(self, sharedId: str):
        gremlinResp = self.g.V().hasLabel("CFGNode").has("sharedId", sharedId).valueMap().toList()

        if len(gremlinResp) == 0:
            return
        else:
            gremlinResp = gremlinResp[0]

        node = CFNode(CFNodeKind[gremlinResp["kind"][0]])
        node.Id = gremlinResp["Id"][0]
        node.sharedId = gremlinResp["sharedId"][0]
        node.setLineOfCode(gremlinResp["line"][0])
        node.setCode(gremlinResp["code"][0])
        return node

    def getDFGNodeBySharedId(self, sharedId: str):
        gremlinResp = self.g.V().hasLabel("DFGNode").has("sharedId", sharedId).valueMap().toList()

        if len(gremlinResp) == 0:
            return
        else:
            gremlinResp = gremlinResp[0]

        node = DFNode()
        node.Id = gremlinResp["Id"][0]
        node.sharedId = gremlinResp["sharedId"][0]
        node.setLineOfCode(gremlinResp["line"][0])
        node.setCode(gremlinResp["code"][0])
        return node

    def findASTNodeInCFG(self, sharedId: str) -> CFNode:
        gResp = self.g.V().hasLabel("CFGNode").has("sharedId", sharedId).valueMap().toList()

        if len(gResp) > 0:
            gResp = gResp[0]
            return self.deserializeCFGNode(gResp)

        currentSharedId = sharedId
        while True:
            currentSharedId = self.g.V().hasLabel("ASTNode").has("sharedId", currentSharedId).inE().outV()\
                                        .values("sharedId").toList()

            # Если это корневой узел
            if len(currentSharedId) == 0:
                return None
            else:
                currentSharedId = currentSharedId[0]

            gResp = self.g.V().hasLabel("CFGNode").has("sharedId", currentSharedId).valueMap().toList()
            if len(gResp) > 0:
                gResp = gResp[0]
                return self.deserializeCFGNode(gResp)

    def findASTNodeInDFG(self, sharedId: str) -> CFNode:
        gResp = self.g.V().hasLabel("DFGNode").has("sharedId", sharedId).valueMap().toList()

        if len(gResp) > 0:
            gResp = gResp[0]
            return self.deserializeDFGNode(gResp), gResp["method"][0]

        currentSharedId = sharedId
        while True:
            currentSharedId = self.g.V().hasLabel("ASTNode").has("sharedId", currentSharedId).inE().outV()\
                                        .values("sharedId").toList()

            # Если это корневой узел
            if len(currentSharedId) == 0:
                return None
            else:
                currentSharedId = currentSharedId[0]

            gResp = self.g.V().hasLabel("DFGNode").has("sharedId", currentSharedId).valueMap().toList()
            if len(gResp) > 0:
                gResp = gResp[0]
                return self.deserializeDFGNode(gResp), gResp["method"][0]

    def deserializeASTNode(self, gremlinResp) -> ASNode:
        node = ASNode(ASNodeKind[gremlinResp["kind"][0]])
        node.Id = gremlinResp["Id"][0]
        node.setLineOfCode(gremlinResp["line"][0])
        node.setCode(gremlinResp["code"][0])
        node.sharedId = gremlinResp["sharedId"][0]
        node.setFile(gremlinResp["file"][0])
        node.optionalProperties = json.loads(gremlinResp["optionalProperties"][0])

        # for k, v in gremlinResp.items():
        #     if hasattr(node, k):
        #         setattr(node, k, v[0])  # index 0 is used because gremlin returns list even for one value
        #     else:
        #         node.setOptionalProperty(k, v[0])
        return node

    def deserializeCFGNode(self, gremlinResp) -> CFNode:
        node = CFNode(CFNodeKind[gremlinResp["kind"][0]])
        node.Id = gremlinResp["Id"][0]
        node.setLineOfCode(gremlinResp["line"][0])
        node.setCode(gremlinResp["code"][0])
        node.setMethod(gremlinResp["method"][0])
        node.sharedId = gremlinResp["sharedId"][0]
        node.setFile(gremlinResp["file"][0])
        node.optionalProperties = json.loads(gremlinResp["optionalProperties"][0])
        # for k, v in gremlinResp.items():
        #     if hasattr(node, k):
        #         setattr(node, k, v[0])  # index 0 is used because gremlin returns list even for one value
        #     else:
        #         node.setOptionalProperty(k, v[0])
        return node

    def deserializeDFGNode(self, gremlinResp) -> DFNode:
        node = DFNode()
        node.Id = gremlinResp["Id"][0]
        node.setLineOfCode(gremlinResp["line"][0])
        node.setCode(gremlinResp["code"][0])
        node.setMethod(gremlinResp["method"][0])
        node.sharedId = gremlinResp["sharedId"][0]
        node.setFile(gremlinResp["file"][0])
        node.DEFs = gremlinResp["DEFs"][0]
        node.USEs = gremlinResp["USEs"][0]
        node.selfFlows = gremlinResp["selfFlows"][0]
        node.IP_DEFs = gremlinResp["IP_DEFs"][0]
        node.optionalProperties = json.loads(gremlinResp["optionalProperties"][0])
        # for k, v in gremlinResp.items():
        #     if hasattr(node, k):
        #         setattr(node, k, v[0])  # index 0 is used because gremlin returns list even for one value
        #     else:
        #         node.setOptionalProperty(k, v[0])
        return node


