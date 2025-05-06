from pathlib import Path

from config import Config
from graphs.cfg.cfg_edge import CFEdgeKind
from plots.graphviz_exporter import ExporterBase

CFG_EDGE_COLORS = {
    CFEdgeKind.TRUE: 'green',
    CFEdgeKind.FALSE: 'red',
    CFEdgeKind.THROWS: 'deeppink4',
    CFEdgeKind.EPS: 'blue'
}

class CFGGraphVizExporter(ExporterBase):
    @staticmethod
    def get_sub_dest_dir() -> Path | str:
        return Config.CFG_PLOTS_DIR

    @staticmethod
    def get_filename_prefix() -> str:
        return "cfg"

    @staticmethod
    def get_edge_color(kind) -> str:
        return CFG_EDGE_COLORS[kind]

    @staticmethod
    def get_additional_edge_attrs(edge_data: dict) -> dict:
        return dict(color=ExporterBase.get_edge_color([edge_data['kind']]), label=edge_data['kind'].name)