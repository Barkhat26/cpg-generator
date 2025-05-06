from pathlib import Path

from graph_builders import AbstractSyntaxForestBuilder
from java.java_class_extractor import JavaClassExtractor
from taint_flow.sinks_manager import SinksManager
from taint_flow.web_framework_kind import WebFrameworkKind


def test_dvja():
    sources_directory = Path(__file__).resolve().parent / "assets" / "dvja" / "src" / "main" / "java"/ "com" / "appsecco" / "dvja"
    asf = AbstractSyntaxForestBuilder.build(sources_directory)
    java_classes = JavaClassExtractor.extract_from_directory(sources_directory)

    sinks_manager = SinksManager(asf, java_classes, WebFrameworkKind.struts2)
    sinks = sinks_manager.get_sinks()
    assert len(sinks) == 92
