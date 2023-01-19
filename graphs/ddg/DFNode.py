from typing import List, Set, Any

from antlr4 import ParserRuleContext

from graphs.digraph import Node


class DFNode(Node):
    def __init__(self):
        super().__init__()
        self.line = 0
        self.code = ""
        self.sharedId = None
        self.method = None
        self.file = None
        self.DEFs: Set[str] = set()
        self.USEs: Set[str] = set()
        self.selfFlows: Set[str] = set()
        self.IP_DEFs = None
        self.optionalProperties = dict()

    def getLineOfCode(self) -> int:
        return self.line

    def setLineOfCode(self, line: int) -> None:
        self.line = line

    def getCode(self) -> str:
        return self.code

    def setCode(self, code: str) -> None:
        self.code = code

    def getSharedId(self):
        return self.sharedId

    def setSharedId(self, ctx: ParserRuleContext):
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

    def addDEF(self, var: str) -> bool:
        if self.hasDEF(var):
            return False
        else:
            self.DEFs.add(var)
            return True

    def hasDEF(self, var) -> bool:
        return var in self.DEFs

    def getAllDEFs(self) -> List[str]:
        return list(self.DEFs)

    def addUSE(self, var: str) -> bool:
        if self.hasUSE(var):
            return False
        else:
            self.USEs.add(var)
            return True

    def hasUSE(self, var: str) -> bool:
        return var in self.USEs

    def getAllUSEs(self) -> List[str]:
        return list(self.USEs)

    def addSelfFlow(self, var: str) -> bool:
        if self.hasSelfFlow(var):
            return False
        else:
            self.selfFlows.add(var)
            return True

    def hasSelfFlow(self, var: str) -> bool:
        return var in self.selfFlows

    def getAllSelfFlows(self) -> List[str]:
        return list(self.selfFlows)

    def containsIPDEFs(self):
        return self.IP_DEFs is not None

    def getOptionalProperties(self):
        return self.optionalProperties

    def getOptionalProperty(self, key: str) -> Any:
        return self.optionalProperties.get(key.lower())

    def setOptionalProperty(self, key: str, value: Any) -> None:
        self.optionalProperties[key.lower()] = value

    def __eq__(self, other):
        if self.Id != other.Id:
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

        if self.DEFs != other.DEFs:
            return False

        if self.USEs != other.USEs:
            return False

        if self.selfFlows != other.selfFlows:
            return False

        if self.IP_DEFs != other.IP_DEFs:
            return False

        if self.optionalProperties.keys() != other.optionalProperties.keys():
            return False

        for k in self.optionalProperties:
            if self.optionalProperties[k] != other.optionalProperties[k]:
                return False

        return True

