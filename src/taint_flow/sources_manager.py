from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.ast.ast_node import ASNode
from java.java_structures import JavaClass
from taint_flow.endpoint_extractors.spring_mvc_endpoint_extractor import SpringMVCEndpointExtractor
from taint_flow.source_patterns import find_source_for_spring_mvc, find_source_by_method_qn_call, find_source_in_params, \
    find_readline
from taint_flow.web_framework_kind import WebFrameworkKind
from utils.dataflow import has_super_class


class SourcesManager:
    def __init__(self, ast: AbstractSyntaxTreeNX, java_classes: dict[str, JavaClass], web_framework: WebFrameworkKind, **web_framework_data):
        self.ast_group = ast
        self.java_classes = java_classes
        self.web_framework = web_framework
        self.web_framework_data = web_framework_data

    def get_sources(self) -> list[ASNode]:
        ast_sources: list[ASNode] = []

        match self.web_framework:
            case WebFrameworkKind.struts2:
                for classQN, jc in self.java_classes.items():
                    if has_super_class(classQN, "ActionSupport", self.java_classes):
                        for field in jc.fields:
                            getter = "get" + field.name[0].upper() + field.name[1:]
                            getter_qn = f"{classQN}.{getter}"
                            ast_sources.extend(find_source_by_method_qn_call(getter_qn, self.ast_group))
                            ast_sources.extend(find_source_in_params(field.name, self.ast_group))

            case WebFrameworkKind.spring_mvc:
                endpoint_extractor = SpringMVCEndpointExtractor(self.web_framework_data.get("views_dir"), self.java_classes)
                endpoint_extractor.extractRouteData()
                controllers_data = endpoint_extractor.routes

                for item in controllers_data:
                    ast_sources.extend(find_source_for_spring_mvc(
                        class_qn=item["class"],
                        method_name=item["method"],
                        params=item["params"],
                        ast=self.ast_group)
                    )
            case _:
                #print("For web framework '%s' does not implement source search" % self.projectConfig["web-framework"])
                ast_sources.extend(find_readline(self.ast_group))

        seen_shared_ids = set()
        new_list: list[ASNode] = []
        for obj in ast_sources:
            if obj.shared_id not in seen_shared_ids:
                new_list.append(obj)
                seen_shared_ids.add(obj.shared_id)

        return new_list
