import argparse
import logging
from pathlib import Path
from enum import Enum

from config import Config
from graph_builders.as_forest_builder import AbstractSyntaxForestBuilder
from graph_builders.ast_builder import ASTBuilder
from graph_builders.cfg_builder import CFGBuilder
from graph_builders.dfg_builder import DFGBuilder
from java.java_class_extractor import JavaClassExtractor
from storage import ASTStorage, CFGStorage, JavaClassesStorage, DFGStorage
from taint_flow.analyzer import TaintFlowAnalyzer
from taint_flow.web_framework_kind import WebFrameworkKind
from log import general_logger as logger, set_global_log_level


class LogLevelArg(Enum):
    none = logging.NOTSET
    info = logging.INFO
    warn = logging.WARN
    error = logging.ERROR
    debug = logging.DEBUG

    @classmethod
    def from_str(cls, log_level_name: str):
        for log_level in list(cls):
            if log_level.name == log_level_name:
                return log_level.value

        return None


def main():
    parser = argparse.ArgumentParser(prog="cpg-analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command")
    subparsers.add_parser("ast", help="Build AST")
    subparsers.add_parser('cfg', help='Build CFG')
    subparsers.add_parser('dfg', help='Build DFG')
    parser_taint = subparsers.add_parser('taint', help='Run taint flow analysis')
    parser_taint.add_argument('--web-framework', choices=['none', 'spring_mvc', 'struts2'],
                              default='none', help='Web framework of analyzed application')

    parser.add_argument('-t', '--target', required=True, help='File or directory to analyze')
    parser.add_argument('--dump-to-db', action='store_true', help='Dump results (ast, cfg, dfg) to sqlite database')
    parser.add_argument('--dump-figures', action='store_true', help='Dump results (ast, cfg, dfg) as figures')
    parser.add_argument('--log-level', choices=[
        LogLevelArg.none.name, LogLevelArg.info.name, LogLevelArg.warn.name, LogLevelArg.error.name, LogLevelArg.debug.name],
                        default=LogLevelArg.info.name)
    parser.add_argument('--log-dir', help='Directory for log and dumped files')

    args = parser.parse_args()
    target = Path(args.target)

    if target.is_file():
        target_is_file = True
    elif target.is_dir():
        target_is_file = False
    else:
        raise Exception("Specify correct target")

    set_global_log_level(LogLevelArg.from_str(args.log_level))

    dump_to_db = args.dump_to_db
    dump_figures = args.dump_figures
    log_dir_param = args.log_dir
    log_dir: Path | None = None

    if dump_figures or dump_to_db:
        if not log_dir_param:
            log_dir = Path(Config.APP_DATA_DIR) / target.name
        else:
            log_dir = Path(log_dir_param)

        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "ast":
        if target_is_file:
            ast = ASTBuilder.build_from_file(target)
        else:
            ast = AbstractSyntaxForestBuilder.build(target)

        if dump_to_db:
            ASTStorage(target.name, dest_dir=log_dir, overwrite=True).dump(ast.g)

        if dump_figures:
            ast.export(log_dir)

    elif args.command == "cfg":
        if target_is_file:
            cfg = CFGBuilder.build_from_file(target)
        else:
            cfg = CFGBuilder.build_from_directory(target)

        if dump_to_db:
            CFGStorage(target.name, dest_dir=log_dir, overwrite=True).dump(cfg.g)

        if dump_figures:
            cfg.export(log_dir)
    elif args.command == "dfg":
        if target_is_file:
            ast = ASTBuilder.build_from_file(target)
            cfg = CFGBuilder.build_from_file(target)
            java_classes = JavaClassExtractor.extract_info_from_file(target)
            dfg_builder = DFGBuilder(ast, cfg, java_classes)
            dfg = dfg_builder.build_from_file(target)
        else:
            ast = AbstractSyntaxForestBuilder.build(target)
            cfg = CFGBuilder.build_from_directory(target)
            java_classes = JavaClassExtractor.extract_from_directory(target)
            dfg_builder = DFGBuilder(ast, cfg, java_classes)
            dfg = dfg_builder.build_from_directory(target)

        if dump_to_db:
            ASTStorage(target.name, dest_dir=log_dir, overwrite=True).dump(ast.g)
            CFGStorage(target.name, dest_dir=log_dir, overwrite=True).dump(cfg.g)
            JavaClassesStorage(target.name, dest_dir=log_dir, overwrite=True).dump(list(java_classes.values()))
            DFGStorage(target.name, dest_dir=log_dir, overwrite=True).dump(dfg.g)

        if dump_figures:
            ast.export(log_dir)
            cfg.export(log_dir)
            dfg.export(log_dir)
    elif args.command == "taint":
        if target_is_file:
            ast = ASTBuilder.build_from_file(target)
            cfg = CFGBuilder.build_from_file(target)
            java_classes = JavaClassExtractor.extract_info_from_file(target)
            dfg_builder = DFGBuilder(ast, cfg, java_classes)
            dfg = dfg_builder.build_from_file(target)
        else:
            ast = AbstractSyntaxForestBuilder.build(target)
            cfg = CFGBuilder.build_from_directory(target)
            java_classes = JavaClassExtractor.extract_from_directory(target)
            dfg_builder = DFGBuilder(ast, cfg, java_classes)
            dfg = dfg_builder.build_from_directory(target)

        if dump_to_db:
            ASTStorage(target.name, dest_dir=log_dir, overwrite=True).dump(ast.g)
            CFGStorage(target.name, dest_dir=log_dir, overwrite=True).dump(cfg.g)
            JavaClassesStorage(target.name, dest_dir=log_dir, overwrite=True).dump(list(java_classes.values()))
            DFGStorage(target.name, dest_dir=log_dir, overwrite=True).dump(dfg.g)

        if dump_figures:
            ast.export(log_dir)
            cfg.export(log_dir)
            dfg.export(log_dir)

        taint_flow_analyzer = TaintFlowAnalyzer(ast, dfg, java_classes, WebFrameworkKind.from_str(args.web_framework))
        taint_flows = taint_flow_analyzer.analyze()

        logger.info(f"Found {len(taint_flows)} taint flows")

        for tf in taint_flows:
            print(tf)


if __name__ == '__main__':
    main()
