import os.path
from pathlib import Path

from antlr.JavaParser import JavaParser
from antlr_visitors import ASTVisitor
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from optional_properties import OptionalProperties
from utils.parsing import get_parse_tree_from_file, get_parse_tree_from_string

class ASTBuilder:
    @staticmethod
    def build_from_file(file_path: Path | str) -> AbstractSyntaxTreeNX:
        file_path = Path(file_path)
        parse_tree = get_parse_tree_from_file(file_path)
        ast = ASTBuilder._build(parse_tree, file_path)

        ast.set_property(OptionalProperties.FilePath, str(file_path))
        package_name = ast.get_property(OptionalProperties.Package)
        base_name = os.path.basename(os.path.splitext(file_path)[0])
        qualified_name = f"{package_name}.{base_name}"

        for v in ast.nodes:
            # TODO: здесь не совсем файл
            v.file = qualified_name
            # TODO: избавиться
            ast.update_node(v)

        return ast

    @staticmethod
    def build_from_string(s: str) -> AbstractSyntaxTreeNX:
        parse_tree = get_parse_tree_from_string(s)
        return ASTBuilder._build(parse_tree)

    @staticmethod
    def _build(parse_tree: JavaParser.CompilationUnitContext, filepath: Path | str = None) -> AbstractSyntaxTreeNX:
        ast = AbstractSyntaxTreeNX()
        visitor = ASTVisitor(ast, filepath)
        visitor.visit(parse_tree)
        return ast
