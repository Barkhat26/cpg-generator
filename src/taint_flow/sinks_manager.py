from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.ast.ast_node import ASNode
from java.java_structures import JavaClass
from taint_flow.sink_patterns import find_create_query, find_execute_query, find_sink_by_method_qn_call, find_sink_in_assignments, \
    find_save_method_calls, find_exec
from utils.dataflow import has_super_class
from taint_flow.web_framework_kind import WebFrameworkKind


class SinksManager:
    def __init__(self, ast: AbstractSyntaxTreeNX, java_classes: dict[str, JavaClass], web_framework: WebFrameworkKind):
        self.web_framework = web_framework
        self.ast_group = ast
        self.java_classes = java_classes

    def get_sinks(self) -> list[ASNode]:
        match self.web_framework:
            case WebFrameworkKind.struts2:
                # ast_sinks = [sink for ast in self.ast_group.values() for sink in find_create_query(ast)]
                ast_sinks = find_create_query(self.ast_group)

                for classQN, jc in self.java_classes.items():
                    if has_super_class(classQN, "ActionSupport", self.java_classes):
                        for field in jc.fields:
                            setter = "set" + field.name[0].upper() + field.name[1:]
                            setter_qn = f"{classQN}.{setter}"
                            # ast_sinks.extend([sink for ast in self.ast_group.values() for sink in find_sink_by_method_qn_call(setter_qn, ast)])
                            ast_sinks.extend(find_sink_by_method_qn_call(setter_qn, self.ast_group))
                            # ast_sinks.extend([sink for ast in self.ast_group.values() for sink in find_sink_in_assignments(field.name, ast)])
                            ast_sinks.extend(find_sink_in_assignments(field.name, self.ast_group))

                # ast_sinks.extend([sink for ast in self.ast_group.values() for sink in find_save_method_calls(ast)])
                ast_sinks.extend(find_save_method_calls(self.ast_group))
                # ast_sinks.extend([sink for ast in self.ast_group.values() for sink in find_exec(ast)])
                ast_sinks.extend(find_exec(self.ast_group))
            case WebFrameworkKind.spring_mvc:
                # ast_sinks = [sink for ast in self.ast_group.values() for sink in find_execute_query(ast)]
                ast_sinks = find_execute_query(self.ast_group)
            case _:
                # ast_sinks = [sink for ast in self.ast_group.values() for sink in find_exec(ast)]
                ast_sinks = find_exec(self.ast_group)

        seen_shared_ids = set()
        new_list: list[ASNode] = []

        for obj in ast_sinks:
            if obj.shared_id not in seen_shared_ids:
                new_list.append(obj)
                seen_shared_ids.add(obj.shared_id)

        return new_list
