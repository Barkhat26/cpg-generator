from enum import Enum, auto
from typing import Dict, Any

from antlr4 import ParserRuleContext

from graphs.digraph import Node


class CFNodeKind(Enum):
    ENTRY = auto()
    ASSIGN = auto()
    IF = auto()
    IF_END = auto()
    EXPR = auto()
    FOR_EXPR = auto()
    FOR_INIT = auto()
    FOR_UPDATE = auto()
    FOR_END = auto()
    WHILE = auto()
    WHILE_END = auto()
    DO_WHILE = auto()
    DO_WHILE_END = auto()
    SWITCH = auto()
    SWITCH_END = auto()
    CASE_STMT = auto()
    BREAK = auto()
    CONTINUE = auto()
    RET = auto()
    TRY = auto()
    TRY_END = auto()
    CATCH = auto()
    CATCH_END = auto()
    FINALLY = auto()
    FINALLY_END = auto()
    RESOURCE = auto()
    THROW = auto()

    def __repr__(self):
        return f"<CFGNodeKind.{self.name}>"


class CFNode(Node):
    def __init__(self, kind: CFNodeKind):
        super().__init__()
        self.kind = kind
        self.line = 0
        self.code = ""
        self.sharedId = None
        self.method = None
        self.file = None
        self.optionalProperties = dict()

    def getKind(self) -> CFNodeKind:
        return self.kind

    def setKind(self, kind: CFNodeKind) -> None:
        self.kind = kind

    def getLineOfCode(self) -> int:
        return self.line

    def setLineOfCode(self, line: int) -> None:
        self.line = line

    def setCode(self, code: str) -> None:
        self.code = code

    def getCode(self) -> str:
        return self.code

    def getSharedId(self) -> str:
        return self.sharedId

    def setSharedId(self, ctx: ParserRuleContext) -> None:
        from utils import getIdByCtx
        self.sharedId = getIdByCtx(ctx)

    def getMethod(self) -> str:
        return self.method

    def setMethod(self, method: str) -> None:
        self.method = method

    def getFile(self) -> str:
        return self.file

    def setFile(self, file: str) -> None:
        self.file = file

    def getOptionalProperties(self) -> Dict[str, Any]:
        return self.optionalProperties

    def setOptionalProperty(self, key: str, value) -> None:
        self.optionalProperties[key] = value

    def getOptionalProperty(self, key):
        return self.optionalProperties.get(key)

    def __eq__(self, other):
        if self.Id != other.Id:
            return False

        if self.kind != other.kind:
            return False

        if self.line != other.line:
            return False

        if self.code != other.code:
            return False

        if self.sharedId != other.sharedId:
            return False

        if self.method != other.method:
            return False

        if self.file != other.file:
            return False

        if self.optionalProperties.keys() != other.optionalProperties.keys():
            return False

        for k in self.optionalProperties:
            if self.optionalProperties[k] != other.optionalProperties[k]:
                return False

        return True

