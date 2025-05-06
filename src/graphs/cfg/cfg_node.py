from enum import Enum, auto
from typing import Dict, Any

from antlr4 import ParserRuleContext

from graphs.digraph import Node


class CFNodeKind(Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

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
    LABEL = auto()
    LABEL_END = auto()
    SYNC = auto()
    SYNC_END = auto()

    def __repr__(self):
        return f"<CFGNodeKind.{self.name}>"


class CFNode(Node):
    def __init__(self,
                 kind: CFNodeKind,
                 node_id=-1,
                 line: int = 0,
                 file: str | None = None,
                 method: str | None = None,
                 code: str = "",
                 shared_id: str | None = None,
                 optional_properties: dict[str, str] | None = None):
        super().__init__(node_id)
        self.kind = kind
        self.line = line
        self.file = file
        self.method = method
        self.code = code
        self.shared_id = shared_id
        self.optional_properties = optional_properties or dict()

    def set_optional_property(self, key: str, value: str) -> None:
        self.optional_properties[key] = value

    def get_optional_property(self, key: str) -> str | None:
        return self.optional_properties.get(key)

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

        if self.method != other.method:
            return False

        if self.file != other.file:
            return False

        if self.optional_properties.keys() != other.optional_properties.keys():
            return False

        for k in self.optional_properties:
            if self.optional_properties[k] != other.optional_properties[k]:
                return False

        return True

