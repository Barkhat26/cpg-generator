from enum import Enum, auto
from typing import Dict, Any

from antlr4 import ParserRuleContext

from graphs.digraph import Node


class ASNodeKind(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.upper()

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
    def __init__(self,
                 kind: ASNodeKind,
                 node_id=-1,
                 file=None,
                 line: int = 0,
                 code: str = "",
                 shared_id: str | None = None,
                 optional_properties: dict[str, str] | None = None):
        super().__init__(node_id)
        self.kind = kind
        self.line = line
        self.file = file
        self.code = code
        self.shared_id = shared_id
        self.optional_properties = optional_properties or dict()

    def get_optional_property(self, key: str) -> Any:
        return self.optional_properties.get(key)

    def set_optional_property(self, key: str, value: Any) -> None:
        self.optional_properties[key] = value

    def __eq__(self, other):
        if self.Id != other.Id:
            return False

        if self.kind != other.kind:
            return False

        if self.line != other.line:
            return False

        if self.code != other.code:
            return False

        if self.shared_id != other.shared_id:
            return False

        if self.file != other.file:
            return False

        if self.optional_properties.keys() != other.optional_properties.keys():
            return False

        for k in self.optional_properties:
            if self.optional_properties[k] != other.optional_properties[k]:
                return False

        return True

    def __repr__(self):
        return f"ASNode(kind={self.kind}, code={self.code}, line={self.line}, file={self.file}, shared_id={self.shared_id})"
