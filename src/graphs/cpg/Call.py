from GremlinDriver import Gremlin
from graphs.ast.ASNode import ASNode, ASNodeKind
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree


class Call:
    def __init__(self, callNode: ASNode, AST: AbstractSyntaxTree):
        self.sharedId = callNode.getSharedId()
        self.AST = AST
        self.name = None
        self.line = callNode.getLineOfCode()
        for outNode in AST.outNodes(callNode):
            if outNode.kind == ASNodeKind.NAME:
                self.name = outNode.getCode()

        gremlin = Gremlin()
        self.params = gremlin.getArgListForCall(self.sharedId)


    def __repr__(self):
        return f"<Call name='{self.name}' params='{self.params}'>"
