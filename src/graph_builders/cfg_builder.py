from pathlib import Path

from antlr_visitors import CFGVisitor
from antlr.JavaParser import JavaParser
from graphs.cfg.control_flow_graph_nx import ControlFlowGraphNX
from utils.parsing import get_parse_tree_from_file, get_parse_tree_from_string


class CFGBuilder:
    @staticmethod
    def build_from_file(filepath: Path | str) -> ControlFlowGraphNX:
        parse_tree = get_parse_tree_from_file(filepath)
        return CFGBuilder._build(parse_tree, filepath=filepath)

    @staticmethod
    def build_from_string(s: str) -> ControlFlowGraphNX:
        parse_tree = get_parse_tree_from_string(s)
        return CFGBuilder._build(parse_tree)

    @staticmethod
    def build_from_directory(sources_directory: Path | str) -> ControlFlowGraphNX:
        _sources_directory = Path(sources_directory)
        cfg = ControlFlowGraphNX()

        for file in _sources_directory.rglob("*.java"):
            parse_tree = get_parse_tree_from_file(file)
            CFGBuilder._fill_cfg(cfg, parse_tree, file)

        return cfg

    @staticmethod
    def _build(parse_tree: JavaParser.CompilationUnitContext, filepath: Path | str = None) -> ControlFlowGraphNX:
        cfg = ControlFlowGraphNX()
        CFGBuilder._fill_cfg(cfg, parse_tree, filepath)
        return cfg

    @staticmethod
    def _fill_cfg(cfg: ControlFlowGraphNX, parse_tree: JavaParser.CompilationUnitContext, filepath: Path | str = None):
        visitor = CFGVisitor(cfg, file_path=filepath)
        visitor.visit(parse_tree)
