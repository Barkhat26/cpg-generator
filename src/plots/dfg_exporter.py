from pathlib import Path
from typing import Iterable

import graphviz
from networkx.classes import Graph

from config import Config
from graphs.ddg.dfg_edge import DFEdge, DFEdgeKind
from plots.graphviz_exporter import ExporterBase


class DFGGraphVizExporter(ExporterBase):
    def __init__(self, cfg: 'ControlFlowGraphNX', dfg_edges: Iterable[DFEdge]):
        self.cfg = cfg  # TODO: избавиться от дублирования Graph и ControlFlowGraph
        self.dfg_edges = dfg_edges


    def add_edges_to_graphviz(self, g: Graph, dot: graphviz.Digraph):
        super().add_edges_to_graphviz(g, dot)

        for dfg_edge in self.dfg_edges:
            # Inter-procedural data-flows are ignored
            if dfg_edge.kind == DFEdgeKind.INTER:
                continue

            cfg_source = self.cfg.get_node_by_shared_id(dfg_edge.source.shared_id)
            cfg_target = self.cfg.get_node_by_shared_id(dfg_edge.target.shared_id)

            dfg_color = "#239da8"
            dot.edge(str(cfg_source.Id), str(cfg_target.Id), label=dfg_edge.label, color=dfg_color, fontcolor=dfg_color)

    @staticmethod
    def get_sub_dest_dir() -> Path | str:
        return Config.DFG_PLOTS_DIR

    @staticmethod
    def get_filename_prefix() -> str:
        return "dfg"

    @staticmethod
    def get_edge_color(kind) -> str:
        return "#239da8"

    @staticmethod
    def get_additional_edge_attrs(edge_data: dict) -> dict:
        return dict(label=edge_data['kind'].name, style="dashed", color="grey", fontcolor="grey")