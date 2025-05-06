from typing import Any

from antlr4 import ParserRuleContext

from graphs.digraph import Node


class DFNode(Node):
    def __init__(self,
                 node_id=-1,
                 line: int = 0,
                 file: str | None = None,
                 method: str | None = None,
                 code: str = "",
                 shared_id: str | None = None,
                 optional_properties: dict[str, str] | None = None,
                 defs: set[str] | None = None,
                 uses: set[str] | None = None,
                 self_flows: set[str] | None = None,
                 ip_defs = None):
        super().__init__(node_id)
        self.line = line
        self.code = code
        self.file = file
        self.method = method
        self.shared_id = shared_id
        self.optional_properties = optional_properties or dict()

        self.defs: set[str] = defs or set()
        self.uses: set[str] = uses or set()
        self.self_flows: set[str] = self_flows or set()
        self.ip_defs = ip_defs or None

    def add_def(self, var: str) -> bool:
        if self.has_def(var):
            return False
        else:
            self.defs.add(var)
            return True

    def has_def(self, var) -> bool:
        return var in self.defs

    def add_use(self, var: str) -> bool:
        if self.has_use(var):
            return False
        else:
            self.uses.add(var)
            return True

    def has_use(self, var: str) -> bool:
        return var in self.uses

    def add_self_flow(self, var: str) -> bool:
        if self.has_self_flow(var):
            return False
        else:
            self.self_flows.add(var)
            return True

    def has_self_flow(self, var: str) -> bool:
        return var in self.self_flows

    def contains_ip_defs(self):
        return self.ip_defs is not None

    def get_optional_property(self, key: str) -> Any:
        return self.optional_properties.get(key.lower())

    def set_optional_property(self, key: str, value: Any) -> None:
        self.optional_properties[key.lower()] = value

    def __eq__(self, other):
        if self.Id != other.Id:
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

        if self.defs != other.defs:
            return False

        if self.uses != other.uses:
            return False

        if self.self_flows != other.self_flows:
            return False

        if self.ip_defs != other.ip_defs:
            return False

        if self.optional_properties.keys() != other.optional_properties.keys():
            return False

        for k in self.optional_properties:
            if self.optional_properties[k] != other.optional_properties[k]:
                return False

        return True

    def __repr__(self):
        return f"DFNode(code={self.code}, file={self.file}, line={self.line})"
