from pathlib import Path

from taint_flow.endpoint_extractors.struts2_endpoint_extractor import Struts2EndpointExtractor


def test1():
    project_directory = Path(__file__).resolve().parent / "assets" / "struts2-demo"
    struts_xml_file = project_directory / "src" / "main" / "resources" / "struts.xml"
    jsp_files_dir = project_directory / "src" / "main" / "webapp"
    endpoint_extractor = Struts2EndpointExtractor(str(jsp_files_dir), str(struts_xml_file))
    endpoint_extractor.extractEndpoints()

    assert len(endpoint_extractor.getViewData()) == 1
    assert len(endpoint_extractor.getRouteData()) == 1