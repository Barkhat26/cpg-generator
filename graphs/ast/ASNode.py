from enum import Enum, auto
from typing import Dict, Any

from antlr4 import ParserRuleContext
from antlr4.tree.Tree import TerminalNodeImpl

from graphs.digraph import Node


class ASNodeKind(Enum):
    ROOT = auto()
    IMPORTS = auto()
    IMPORT = auto()
    PACKAGE = auto()
    NAME = auto()
    MODIFIER = auto()
    CLASS = auto()
    EXTENDS = auto()
    IMPLEMENTS = auto()
    INTERFACE = auto()
    STATIC_BLOCK = auto()
    CONSTRUCTOR = auto()
    FIELD = auto()
    TYPE = auto()
    METHOD = auto()
    RET_VAL_TYPE = auto()
    PARAMS = auto()
    BLOCK = auto()
    IF = auto()
    CONDITION = auto()
    THEN = auto()
    ELSE = auto()
    VARIABLE = auto()
    INIT_VALUE = auto()
    STATEMENT = auto()
    RETURN = auto()
    FOR = auto()
    FOR_INIT = auto()
    FOR_UPDATE = auto()
    FOR_EACH = auto()
    FOR_IN = auto()
    WHILE = auto()
    DO_WHILE = auto()
    TRY = auto()
    RESOURCES = auto()
    CATCH = auto()
    FINALLY = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    LABELED = auto()
    SYNC = auto()
    ARITH = auto()
    LITERAL = auto()
    CALL = auto()
    DOT = auto()
    ARRAY = auto()
    ASSIGN = auto()
    ASSIGN_LEFT = auto()
    ASSIGN_RIGHT = auto()
    BOP = auto()
    UNARY = auto()
    CAST = auto()
    ARRAY_INIT = auto()
    ARGS = auto()
    TERNARY = auto()
    TERNARY_PREDICATE = auto()
    TERNARY_TRUE = auto()
    TERNARY_FALSE = auto()


class ASNode(Node):
    def __init__(self, kind: ASNodeKind):
        super().__init__()
        self.kind = kind
        self.line = 0
        self.code = ""
        self.sharedId = None
        self.file = None
        self.optionalProperties = dict()

    def getKind(self) -> ASNodeKind:
        return self.kind

    def setKind(self, kind: ASNodeKind) -> None:
        self.kind = kind

    def getLineOfCode(self) -> int:
        return self.line

    def setLineOfCode(self, line: int) -> None:
        self.line = line

    def getCode(self) -> str:
        return self.code

    def setCode(self, code: str) -> None:
        self.code = code

    def getSharedId(self) -> str:
        return self.sharedId

    def setSharedId(self, ctx: ParserRuleContext) -> None:
        from utils import getIdByCtx
        self.sharedId = getIdByCtx(ctx)

    def getFile(self) -> str:
        return self.file

    def setFile(self, file: str) -> None:
        self.file = file

    def getOptionalProperties(self) -> Dict[str, Any]:
        return self.optionalProperties

    def getOptionalProperty(self, key: str) -> Any:
        return self.optionalProperties.get(key)

    def setOptionalProperty(self, key: str, value: Any) -> None:
        self.optionalProperties[key] = value

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

        if self.file != other.file:
            return False

        if self.optionalProperties.keys() != other.optionalProperties.keys():
            return False

        for k in self.optionalProperties:
            if self.optionalProperties[k] != other.optionalProperties[k]:
                return False

        return True
