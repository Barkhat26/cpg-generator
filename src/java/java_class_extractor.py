from pathlib import Path

from antlr.JavaParser import JavaParser
from antlr_visitors.java_class_visitor import JavaClassVisitor
from java.java_structures import JavaClass
from utils.parsing import get_parse_tree_from_file, get_parse_tree_from_string


class JavaClassExtractor:
    @staticmethod
    def extract_info_from_file(file_path: Path | str) -> dict[str, JavaClass]:
        _file_path = Path(file_path)
        parse_tree = get_parse_tree_from_file(_file_path)
        return JavaClassExtractor._extract_info(parse_tree, _file_path)

    @staticmethod
    def extract_info_from_string(code: str) -> dict[str, JavaClass]:
        parse_tree = get_parse_tree_from_string(code)
        return JavaClassExtractor._extract_info(parse_tree)

    @staticmethod
    def extract_from_directory(sources_directory: Path | str) -> dict[str, JavaClass]:
        _sources_directory = Path(sources_directory)
        java_classes: dict[str, JavaClass] = {}

        for file in _sources_directory.rglob("*.java"):
            java_classes.update(JavaClassExtractor.extract_info_from_file(file))

        return java_classes

    @staticmethod
    def _extract_info(parse_tree: JavaParser.CompilationUnitContext, file_path: str | Path = None) -> dict[str, JavaClass]:
        java_classes: dict[str, JavaClass] = {}
        visitor = JavaClassVisitor(file_path, java_classes)
        visitor.visit(parse_tree)
        return java_classes




