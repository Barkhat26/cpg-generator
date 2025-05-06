from graph_dsl import Query
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.ast.ast_node import ASNode, ASNodeKind
from graphs.ddg.data_flow_graph_nx import DataFlowGraphNX
from graphs.ddg.dfg_node import DFNode
from java.java_structures import JavaClass
from log import taint_flow_analyzer_logger as logger
from optional_properties import OptionalProperties
from taint_flow.sinks_manager import SinksManager
from taint_flow.sources_manager import SourcesManager
from taint_flow.taintflow import TaintFlow
from taint_flow.utils import check_df_reachability, delete_duplicate_taint_flows
from taint_flow.web_framework_kind import WebFrameworkKind


class TaintFlowAnalyzer:
    def __init__(self, ast: AbstractSyntaxTreeNX, dfg: DataFlowGraphNX, java_classes: dict[str, JavaClass], web_framework: WebFrameworkKind, **web_framework_data):
        self.ast_group = ast
        self.dfg = dfg
        self.sources_manager = SourcesManager(ast, java_classes, web_framework, **web_framework_data)
        self.sinks_manager = SinksManager(ast, java_classes, web_framework)

    def analyze(self) -> list[TaintFlow]:
        ast_sources = self.sources_manager.get_sources()
        ast_sources_with_dfsp = [(ast_source, self.find_ast_node_in_dfg(ast_source)) for ast_source in ast_sources]
        ast_sinks = self.sinks_manager.get_sinks()
        ast_sinks_with_dftp = [(ast_sink, self.find_ast_node_in_dfg(ast_sink)) for ast_sink in ast_sinks]

        logger.info(f"Found {len(ast_sources)} sources")
        if len(ast_sources) == 0:
            return []

        logger.info(f"Found {len(ast_sinks)} sinks")
        if len(ast_sinks) == 0:
            return []

        taint_flows: list[TaintFlow] = []

        for ast_sink, dftp in ast_sinks_with_dftp:
            logger.info(f"\t{ast_sink.get_optional_property(OptionalProperties.SinkText)} in file {ast_sink.file} at line {ast_sink.line} (sharedId: {ast_sink.shared_id})")
            logger.info(f"\t\tDFG-node sharedId: {dftp.shared_id}")

            if ast_sink.get_optional_property(OptionalProperties.Args):
                dftp.set_optional_property(OptionalProperties.Checkpoint, ast_sink.get_optional_property("args")[0])
            elif ast_sink.get_optional_property(OptionalProperties.AssignmentExpression):
                dftp.set_optional_property(OptionalProperties.Checkpoint, ast_sink.get_optional_property(OptionalProperties.AssignmentExpression))

            for ast_source, dfsp in ast_sources_with_dfsp:
                logger.info(f"\t\t\t{ast_source.get_optional_property(OptionalProperties.SourceText)} in file {ast_source.file} at line {ast_source.line} (sharedId: {ast_source.shared_id})")
                logger.info(f"\t\t\t\tDFG-node sharedId: {dfsp.shared_id}")

                if check_df_reachability(self.dfg, dfsp.shared_id, dftp.shared_id):
                    taint_flows.append(TaintFlow(
                        source=dfsp,
                        sink=dftp,
                        vulnerability=ast_sink.get_optional_property(OptionalProperties.Vulnerability))
                    )

        taint_flows = delete_duplicate_taint_flows(taint_flows)
        return taint_flows

    def find_ast_node_in_dfg(self, ast_node: ASNode) -> DFNode | None:
        g_resp = Query(self.dfg.g).V().has("shared_id", ast_node.shared_id).nodes()

        assert len(g_resp) < 2

        if len(g_resp) > 0:
            return self.dfg.get_node_by_id(g_resp[0])

        # current_shared_id = shared_id
        current_ast_node = ast_node

        while True:
            parent: ASNode | None = None
            # current_shared_ids = []
            # for ast in self.ast_group.values():
            if parent_id := self.ast_group.in_nodes(current_ast_node.Id)[0]:
                parent = self.ast_group.get_node_by_id(parent_id)

                # for shared_id in Query(ast.g).has("shared_id", current_shared_id).inE().outV().values("shared_id"):
                #     current_shared_ids.append(shared_id)

            # assert len(current_shared_ids) == 1
            assert parent is not None

            # TODO: по другому проверять, что это Root-узел
            # Если это корневой узел
            # if len(current_shared_ids) == 1 and current_shared_ids[0] is None:
            #     return None
            # else:
            #     current_shared_id = current_shared_ids[0]

            if parent.kind == ASNodeKind.ROOT:
                return None
            else:
                current_ast_node = parent

            g_resp = Query(self.dfg.g).V().has("shared_id", current_ast_node.shared_id).nodes()

            if len(g_resp) > 0:
                return self.dfg.get_node_by_id(g_resp[0])
