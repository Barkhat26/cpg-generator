from typing import List

class MethodDefInfo:
    def __init__(self, ret: str, name: str, pkg: str, cls: str, args: List[str], Id: tuple):
        self.NAME = name
        self.RET_TYPE = ret
        self.CLASS_NAME = cls
        self.PACKAGE = "" if pkg is None else pkg
        self.PARAMS = [] if args is None else args

        self.fieldDEFs = []
        self.stateDEF = self.guessByTypeOrName()
        self.argDEFs = [False] * len(self.PARAMS)
        self.ID = Id

    def guessByTypeOrName(self) -> bool:
        if self.RET_TYPE is None:
            return True

        prefixes = ["set", "put", "add", "insert", "push", "append"]
        for pre in prefixes:
            if self.NAME.lower().startswith(pre):
                return True

        return False

    def doesStateDEF(self) -> bool:
        return self.stateDEF

    def argDEFs(self) -> List[bool]:
        return self.argDEFs

    def setArgDEF(self, argIndex: int,  DEF: bool) -> None:
        self.argDEFs[argIndex] = DEF

    def setAllArgDEFs(self, argDefs: List[bool]) -> None:
        self.argDEFs = argDefs

    def fieldDEFs(self, str) -> List[str]:
        return self.fieldDEFs

    def addFieldDEF(self, fieldName: str) -> None:
        if fieldName not in self.fieldDEFs:
            self.fieldDEFs.append(fieldName)
            self.stateDEF = True

class JavaField:
    def __init__(self, modifier: str, isStatic: bool, type: str, name: str):
        self.name = name
        self.type = type
        self.isStatic = isStatic
        self.modifier = modifier

class JavaClass:
    def __init__(self, name: str, package: str, extends: str, filePath: str, imports: List[str],
                 modifiers: List[str], annotations: List[str]):
        self.name = name
        self.package = package
        self.filePath = filePath
        self.extends = extends
        self.imports = imports
        self.implementations = []
        self.fieldList = []
        self.methods = []

        self.typeParameters = None
        self.code = ""
        self.modifiers = modifiers
        self.annotations = annotations

    def setInterfaces(self, intfs: List[str]):
        self.implementations = intfs

    def addMethod(self, mtd):
        self.methods.append(mtd)

    def addField(self, field):
        self.fieldList.append(field)

    def getAllFields(self):
        return self.fieldList


class JavaMethod:
    def __init__(self, modifier: str, isStatic: bool, isAbstract: bool,
                 retType: str, name: str, args: List[dict], line: int, sharedId: tuple,
                 annotations: List[str]):
        self.name = name
        self.isStatic = isStatic
        self.isAbstract = isAbstract
        self.modifier = modifier
        self.retType = retType
        self.args = args
        self.line = line
        self.sharedId = sharedId
        self.annotations = annotations

