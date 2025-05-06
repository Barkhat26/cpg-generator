from pathlib import Path

from config import Config
from plots.graphviz_exporter import ExporterBase


class AbstractSyntaxGraphVizExporter(ExporterBase):
    @staticmethod
    def get_sub_dest_dir() -> Path | str:
        return Config.AST_PLOTS_DIR

    @staticmethod
    def get_filename_prefix() -> str:
        return "ast"

    @staticmethod
    def get_edge_color(kind) -> str:
        return "#008800"