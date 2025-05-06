from pathlib import Path

from antlr.JavaParser import JavaParser
from antlr_visitors import DFGVisitor
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.cfg.control_flow_graph_nx import ControlFlowGraphNX
from graphs.ddg.data_flow_graph_nx import DataFlowGraphNX
from graphs.cfg.cfg_path_traversal import CFPathTraversal
from graphs.ddg.dfg_edge import DFEdgeKind
from java.java_structures import JavaClass
from utils.parsing import get_parse_tree_from_file, get_parse_tree_from_string
from log import dfg_builder_logger as logger


class DFGBuilder:
    def __init__(self, ast: AbstractSyntaxTreeNX, cfg: ControlFlowGraphNX, java_classes: dict[str, JavaClass]):
        self.ast = ast
        self.cfg = cfg
        self.java_classes = java_classes

    def build_from_file(self, file_path: Path | str) -> DataFlowGraphNX:
        _file_path = Path(file_path)
        parse_tree = get_parse_tree_from_file(_file_path)
        return self._build(parse_tree, _file_path)

    def build_from_string(self, s: str) -> DataFlowGraphNX:
        parse_tree = get_parse_tree_from_string(s)
        return self._build(parse_tree)

    def build_from_directory(self, sources_directory: Path | str) -> DataFlowGraphNX:
        _sources_directory = Path(sources_directory)
        dfg = DataFlowGraphNX()

        for file in _sources_directory.rglob("*.java"):
            parse_tree = get_parse_tree_from_file(file)
            self._fill_dfg(dfg, parse_tree, file)

        return dfg

    def _build(self, parse_tree: JavaParser.CompilationUnitContext, file_path: Path = None) -> DataFlowGraphNX:
        dfg = DataFlowGraphNX()
        self._fill_dfg(dfg, parse_tree, file_path)
        return dfg

    def _fill_dfg(self, dfg: DataFlowGraphNX, parse_tree: JavaParser.CompilationUnitContext, file_path=None):
        # Extract the information of all given Java classes
        # logger.info("\nExtracting class-infos ... ")
        # classesList = JavaClassExtractor.extractInfo(filename, parseTree)
        # allClassInfos = dict()
        # for cls in classesList:
        #     allClassInfos[cls.name] = cls
        # logger.info("Done.")

        # Initialize method DEF information
        # logger.info("\nInitializing method-DEF infos ... ")
        # methodDEFs = dict()
        # for cls in classesList:
        #     for mtd in cls.methods:
        #         lst = methodDEFs.get(mtd.name)
        #         if lst is None:
        #             lst = []
        #             lst.append(MethodDefInfo(mtd.retType, mtd.name, cls.package, cls.name, mtd.args, mtd.sharedId))
        #             methodDEFs[mtd.name] = lst
        #         else:
        #             lst.append(MethodDefInfo(mtd.retType, mtd.name, cls.package, cls.name, mtd.args, mtd.sharedId))
        # logger.info("Done.")

        # Analyze method DEF information for imported libraries
        # TODO implement
        pass

        logger.info("Iterative DEF-USE analysis ... ")
        iteration = 0

        while True:
            iteration += 1
            changed = False
            visitor = DFGVisitor(
                iteration=iteration,
                ddg=dfg,
                cfg=self.cfg,
                ast=self.ast,
                java_classes=self.java_classes,
                file_path=file_path
            )
            visitor.visit(parse_tree)
            changed |= visitor.changed
            logger.debug("Iteration #" + str(iteration) + ": " + ("CHANGED" if changed else "NO-CHANGE"))
            logger.debug("========================================")

            if not changed:
                break

        logger.info("Done.")

        # for qn, dfg in self.DFG.items():
        #     dfg.cfg = self.cfg.get(qn)
        dfg.cfg = self.cfg

        logger.info("Adding data-flows...")
        self.add_intra_procedural_edges(dfg)
        self.add_inter_procedural_edges(dfg)

    @staticmethod
    def add_intra_procedural_edges(dfg: DataFlowGraphNX):
        visited_defs = set()

        cfg = dfg.cfg
        visited_defs.clear()

        for entry in cfg.entries.values():
            def_traversal = CFPathTraversal(cfg, entry)

            while def_traversal.has_next():
                def_cf_node = def_traversal.next()

                if def_cf_node.Id in visited_defs:
                    def_traversal.continue_next_path()
                    continue
                visited_defs.add(def_cf_node.Id)

                def_dd_node = dfg.get_node_by_shared_id(def_cf_node.shared_id)
                if def_dd_node is None:
                    continue

                if len(def_dd_node.defs) == 0 and not def_dd_node.contains_ip_defs():
                    continue

                # first add any self-flows of this node
                for flow in def_dd_node.self_flows:
                    dfg.add_edge(def_dd_node, def_dd_node, flow)

                # now traverse the CFG for any USEs till a DEF
                visited_uses = set()
                for DEF in def_dd_node.defs:
                    use_traversal = CFPathTraversal(cfg, def_cf_node)
                    visited_uses.clear()
                    use_cf_node = use_traversal.next()
                    visited_uses.add(use_cf_node.Id)

                    while use_traversal.has_next():
                        use_cf_node = use_traversal.next()
                        use_dd_node = dfg.get_node_by_shared_id(use_cf_node.shared_id)

                        if use_dd_node is None:
                            continue

                        if use_dd_node.has_def(DEF):
                            use_traversal.continue_next_path()  # no need to continue this path

                        if use_cf_node.Id in visited_uses:
                            use_traversal.continue_next_path()  # no need to continue this path

                        else:
                            visited_uses.add(use_cf_node.Id)
                            if use_dd_node.has_use(DEF):
                                dfg.add_edge(def_dd_node, use_dd_node, DEF)

    @staticmethod
    def add_inter_procedural_edges(dfg: DataFlowGraphNX):
        for node in dfg.nodes:
            if node.ip_defs is not None:
                ipdf_target = dfg.get_node_by_shared_id(node.ip_defs["entrySharedId"])
                dfg.add_edge(node, ipdf_target, "inter-procedural", DFEdgeKind.INTER)