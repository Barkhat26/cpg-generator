from pathlib import Path
import subprocess

from config import Config
from dynamic.checkpoint_manager import CheckpointManager
from dynamic.instrument_tool import InstrumentTool
from dynamic.simple_cli_attacker import SimpleCLIAttacker
from graph_builders import ASTBuilder, CFGBuilder, DFGBuilder
from java.java_class_extractor import JavaClassExtractor
from taint_flow.analyzer import TaintFlowAnalyzer
from taint_flow.web_framework_kind import WebFrameworkKind


def test_command_executor():
    file = Path(__file__).resolve().parent / "assets" / "original_command_executor" / "CommandExecutor.java"
    ast = ASTBuilder.build_from_file(file)
    cfg = CFGBuilder.build_from_file(file)
    java_classes = JavaClassExtractor.extract_info_from_file(file)
    dfg_builder = DFGBuilder(
        ast=ast,
        cfg=cfg,
        java_classes=java_classes
    )
    dfg = dfg_builder.build_from_file(file)
    taint_flow_analyzer = TaintFlowAnalyzer(ast, dfg, java_classes, WebFrameworkKind.none)
    taint_flows = taint_flow_analyzer.analyze()

    project_name = "command_executor"
    checkpoint_manager = CheckpointManager(project_name, taint_flows)
    checkpoint_manager.prepare()
    tool = InstrumentTool(project_name, checkpoint_manager)
    file_modifications = tool.instrument()

    assert len(file_modifications) == 1

    file_modification = file_modifications[0]
    build_dir = Config.APP_DATA_DIR / "out"

    proc = subprocess.run([
        'javac',
        '-cp', Config.CHECKPOINT_SAVER_PATH,
        '-d', build_dir,
        file_modification.out_file
    ], stderr=subprocess.PIPE)

    assert proc.returncode == 0

    attacker = SimpleCLIAttacker(checkpoint_manager, [
        'java',
        '-cp', f'{Config.CHECKPOINT_SAVER_PATH};{build_dir}',
        'CommandExecutor'
    ])
    attack_is_successful = attacker.attack()

    assert attack_is_successful

    built_file = (build_dir / file_modification.out_file.stem).with_suffix(".class")
    built_file.unlink()
