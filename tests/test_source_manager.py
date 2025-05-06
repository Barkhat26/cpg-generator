from pathlib import Path

from graph_builders import AbstractSyntaxForestBuilder
from java.java_class_extractor import JavaClassExtractor
from taint_flow.sources_manager import SourcesManager
from taint_flow.web_framework_kind import WebFrameworkKind


def test_dvja():
    sources_directory = Path(__file__).resolve().parent / "assets" / "dvja" / "src" / "main" / "java" / "com" / "appsecco" / "dvja" / "controllers"
    asf = AbstractSyntaxForestBuilder.build(sources_directory)
    java_classes = JavaClassExtractor.extract_from_directory(sources_directory)

    sources_manager = SourcesManager(asf, java_classes, WebFrameworkKind.struts2)
    sources = sources_manager.get_sources()
    assert len(sources) == 61
