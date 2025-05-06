import os
from pathlib import Path

from antlr_visitors import ASTVisitor
from graphs.ast.abstract_syntax_forest import AbstractSyntaxForest
from utils.parsing import get_parse_tree_from_file


class AbstractSyntaxForestBuilder:
    @staticmethod
    def build(sources_directory: Path) -> AbstractSyntaxForest:
        abstract_syntax_forest = AbstractSyntaxForest()

        for file in sources_directory.rglob("*.java"):
            parse_tree = get_parse_tree_from_file(file)
            visitor = ASTVisitor(abstract_syntax_forest, str(file))
            visitor.visit(parse_tree)
            qn = os.path.splitext(os.path.relpath(file, sources_directory).replace(os.sep, '.'))[0]
            abstract_syntax_forest.roots[qn] = visitor.root

        return abstract_syntax_forest