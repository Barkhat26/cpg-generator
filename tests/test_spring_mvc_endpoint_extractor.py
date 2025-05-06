from pathlib import Path

from java.java_class_extractor import JavaClassExtractor
from taint_flow.endpoint_extractors.spring_mvc_endpoint_extractor import SpringMVCEndpointExtractor


def test_spring_mvc_demo():
    sources_directory = Path(__file__).resolve().parent / "assets" / "spring-mvc-demo"
    java_classes = JavaClassExtractor.extract_from_directory(sources_directory)

    views_dir = Path(__file__).resolve().parent / "assets" / "spring-mvc-demo" / "src" / "main" / "webapp" / "WEB-INF" / "views"
    extractor = SpringMVCEndpointExtractor(str(views_dir), java_classes)
    extractor.extractEndpoints()
    assert len(extractor.routes) == 3
    assert len(extractor.forms) == 1
