from pathlib import Path
from typing import List

# TODO: перенести из этого файла
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

# TODO: переделать в dataclass
class JavaField:
    def __init__(self, modifier: str | None, is_static: bool, field_type: str, name: str):
        self.name = name
        self.type = field_type
        self.is_static = is_static
        self.modifier = modifier

class JavaAnnotation:
    def __init__(self, name: str, values: list[str]):
        self.name = name
        self.values = values

class JavaArg:
    def __init__(self, is_final: bool, annotations: list[JavaAnnotation], type_: str, name: str):
        self.is_final = is_final
        self.annotations = annotations
        self.type = type_
        self.name = name

# TODO: переделать в dataclass
class JavaMethod:
    def __init__(self,
                 modifier: str,
                 is_static: bool,
                 is_abstract: bool,
                 ret_type: str | None,
                 name: str,
                 args: list[JavaArg],
                 line: int,
                 shared_id: str,
                 annotations: list[JavaAnnotation]):
        self.name = name
        self.is_static = is_static
        self.is_abstract = is_abstract
        self.modifier = modifier
        self.ret_type = ret_type
        self.args = args
        self.line = line
        self.shared_id = shared_id
        self.annotations = annotations

class JavaClass:
    def __init__(self,
                 name: str,
                 package: str,
                 extends: str,
                 file_path: Path | str,
                 imports: list[str],
                 modifiers: list[str],
                 annotations: list[JavaAnnotation],
                 interfaces: list[str] | None = None,
                 fields: list[JavaField] | None = None,
                 methods: list[JavaMethod] | None = None,
                 type_parameters = None,
                 code = ""):
        self.name = name
        self.package = package
        self.filePath = file_path
        self.extends = extends
        self.imports = imports
        self.interfaces = interfaces or []
        self.fields: list[JavaField] = fields or []
        self.methods: list[JavaMethod] = methods or []

        self.typeParameters = type_parameters
        self.code = code
        self.modifiers = modifiers
        self.annotations = annotations

    def add_method(self, method: JavaMethod):
        self.methods.append(method)

    def add_field(self, field: JavaField):
        self.fields.append(field)

    def get_method_by_name(self, method_name: str) -> JavaMethod | None:
        for method in self.methods:
            if method.name == method_name:
                return method

        return None

    def __repr__(self):
        return f"JavaClass(name={self.name}, package={self.package})"




