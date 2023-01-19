from marshmallow import Schema, fields, post_load
from marshmallow_enum import EnumField

from JavaStructures import JavaField, JavaMethod, JavaClass
from graphs.ast.ASEdge import ASEdge
from graphs.ast.ASNode import ASNodeKind, ASNode
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cfg.CFEdge import CFEdge, CFEdgeKind
from graphs.cfg.CFNode import CFNode, CFNodeKind
from graphs.cfg.ControlFlowGraph import ControlFlowGraph

# ***********************************************
# ***         Abstract Syntax Tree            ***
# ***********************************************
from graphs.ddg.DFEdge import DFEdge, DFEdgeKind
from graphs.ddg.DFNode import DFNode
from graphs.ddg.DataFlowGraph import DataFlowGraph


class ASNodeSchema(Schema):
    Id = fields.Integer()
    kind = EnumField(ASNodeKind)
    line = fields.Integer()
    code = fields.String()
    sharedId = fields.String(allow_none=True)
    file = fields.String(allow_none=True)
    optionalProperties = fields.Dict()

    @post_load
    def makeASNode(self, data, **kwargs):
        asNode = ASNode(data["kind"])
        asNode.Id = data["Id"]
        asNode.line = data["line"]
        asNode.code = data["code"]
        asNode.sharedId = data["sharedId"]
        asNode.file = data["file"]
        asNode.optionalProperties = data["optionalProperties"]
        return asNode


class ASEdgeSchema(Schema):
    source = fields.Nested(ASNodeSchema())
    label = fields.String(allow_none=True)
    target = fields.Nested(ASNodeSchema())

    @post_load
    def makeASEdge(self, data, **kwargs):
        return ASEdge(**data)


class AbstractSyntaxTreeSchema(Schema):
    nodes = fields.List(fields.Nested(ASNodeSchema()))
    allEdges = fields.List(fields.Nested(ASEdgeSchema()))
    inEdges = fields.Dict(keys=fields.Int(), values=fields.List(fields.Nested(ASEdgeSchema())))
    outEdges = fields.Dict(keys=fields.Int(), values=fields.List(fields.Nested(ASEdgeSchema())))
    properties = fields.Dict()

    @post_load
    def makeAbstractSyntaxTree(self, data, **kwargs):
        AST = AbstractSyntaxTree()
        AST.nodes = data["nodes"]
        AST.allEdges = data["allEdges"]
        AST.inEdges = data["inEdges"]
        AST.outEdges = data["outEdges"]
        AST.properties = data["properties"]
        return AST


# ****************************************************
# ***             Control Flow Graph               ***
# ****************************************************


class CFNodeSchema(Schema):
    Id = fields.Integer()
    kind = EnumField(CFNodeKind)
    line = fields.Integer()
    code = fields.String()
    sharedId = fields.String(allow_none=True)
    method = fields.String(allow_none=True)
    file = fields.String()
    optionalProperties = fields.Dict()

    @post_load
    def makeCFNode(self, data, **kwargs):
        cfNode = CFNode(data["kind"])
        cfNode.Id = data["Id"]
        cfNode.line = data["line"]
        cfNode.code = data["code"]
        cfNode.sharedId = data["sharedId"]
        cfNode.method = data["method"]
        cfNode.file = data["file"]
        cfNode.optionalProperties = data["optionalProperties"]
        return cfNode


class CFEdgeSchema(Schema):
    source = fields.Nested(CFNodeSchema())
    label = EnumField(CFEdgeKind)
    target = fields.Nested(CFNodeSchema())

    @post_load
    def makeCFEdge(self, data, **kwargs):
        return CFEdge(**data)


class ControlFlowGraphSchema(Schema):
    nodes = fields.List(fields.Nested(CFNodeSchema()))
    allEdges = fields.List(fields.Nested(CFEdgeSchema()))
    inEdges = fields.Dict(keys=fields.Int(), values=fields.List(fields.Nested(CFEdgeSchema())))
    outEdges = fields.Dict(keys=fields.Int(), values=fields.List(fields.Nested(CFEdgeSchema())))
    properties = fields.Dict()

    @post_load
    def makeControlFlowGraph(self, data, **kwargs):
        cfg = ControlFlowGraph()
        cfg.nodes = data["nodes"]
        cfg.allEdges = data["allEdges"]
        cfg.inEdges = data["inEdges"]
        cfg.outEdges = data["outEdges"]
        cfg.properties = data["properties"]
        return cfg

# ************************************************
# ***            Data Flow Graph               ***
# ************************************************


class DFNodeSchema(Schema):
    Id = fields.Integer()
    line = fields.Integer()
    code = fields.String()
    sharedId = fields.String(allow_none=True)
    method = fields.String(allow_none=True)
    file = fields.String()
    DEFs = fields.List(fields.String())
    USEs = fields.List(fields.String())
    selfFlows = fields.List(fields.String())
    IP_DEFs = fields.Dict(allow_none=True)
    optionalProperties = fields.Dict()

    @post_load
    def makeDFNode(self, data, **kwargs):
        dfNode = DFNode()
        dfNode.Id = data["Id"]
        dfNode.line = data["line"]
        dfNode.code = data["code"]
        dfNode.sharedId = data["sharedId"]
        dfNode.method = data["method"]
        dfNode.file = data["file"]
        dfNode.DEFs = data["DEFs"]
        dfNode.USEs = data["USEs"]
        dfNode.selfFlows = data["selfFlows"]
        dfNode.IP_DEFs = data["IP_DEFs"]
        dfNode.optionalProperties = data["optionalProperties"]
        return dfNode


class DFEdgeSchema(Schema):
    source = fields.Nested(DFNodeSchema())
    label = fields.String()
    target = fields.Nested(DFNodeSchema(), allow_none=True)
    kind = EnumField(DFEdgeKind)

    @post_load
    def makeDFEdge(self, data, **kwargs):
        return DFEdge(**data)


class DataFlowGraphSchema(Schema):
    nodes = fields.List(fields.Nested(DFNodeSchema()))
    allEdges = fields.List(fields.Nested(DFEdgeSchema()))
    inEdges = fields.Dict(keys=fields.Int(), values=fields.List(fields.Nested(DFEdgeSchema())))
    outEdges = fields.Dict(keys=fields.Int(), values=fields.List(fields.Nested(DFEdgeSchema())))
    properties = fields.Dict()

    @post_load
    def makeDataFlowGraph(self, data, **kwargs):
        dfg = DataFlowGraph()
        dfg.nodes = data["nodes"]
        dfg.allEdges = data["allEdges"]
        dfg.inEdges = data["inEdges"]
        dfg.outEdges = data["outEdges"]
        dfg.properties = data["properties"]
        return dfg


# ****************************************************
# ***              Java Classes                    ***
# ****************************************************


class JavaFieldSchema(Schema):
    name = fields.String()
    type = fields.String()
    isStatic = fields.String()
    modifier = fields.String(allow_none=True)

    @post_load
    def makeJavaField(self, data, **kwargs):
        return JavaField(**data)


class JavaMethodSchema(Schema):
    name = fields.String()
    isStatic = fields.Boolean()
    isAbstract = fields.Boolean()
    modifier = fields.String(allow_none=True)
    retType = fields.String(allow_none=True)
    args = fields.List(fields.Dict())
    line = fields.Integer()
    sharedId = fields.String()
    annotations = fields.List(fields.Dict(keys=fields.String()))

    @post_load
    def makeJavaMethod(self, data, **kwargs):
        return JavaMethod(**data)


class JavaClassSchema(Schema):
    name = fields.String()
    package = fields.String()
    filePath = fields.String()
    extends = fields.String(allow_none=True)
    imports = fields.List(fields.String())
    implementations = fields.List(fields.String())
    fieldList = fields.List(fields.Nested(JavaFieldSchema()))
    methods = fields.List(fields.Nested(JavaMethodSchema()))
    typeParameters = fields.String(allow_none=True)
    code = fields.String()
    modifiers = fields.List(fields.String())
    annotations = fields.List(fields.Dict(keys=fields.String()))

    @post_load
    def makeJavaClass(self, data, **kwargs):
        javaClass = JavaClass(
            name=data["name"],
            package=data["package"],
            extends=data["extends"],
            filePath=data["filePath"],
            imports=data["imports"],
            modifiers=data["modifiers"],
            annotations=data["annotations"]
        )
        javaClass.implementations = data["implementations"]
        javaClass.fieldList = data["fieldList"]
        javaClass.methods = data["methods"]
        javaClass.typeParameters = data["typeParameters"]
        javaClass.code = data["code"]

        return javaClass


class TaintFlowSchema(Schema):
    source = fields.Nested(DFNodeSchema())
    vulnerability = fields.String()
    sink = fields.Nested(DFNodeSchema())

