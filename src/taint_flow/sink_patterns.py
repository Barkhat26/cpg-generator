import json

from graph_dsl import Query, __
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.ast.ast_node import ASNodeKind
from optional_properties import OptionalProperties


# --------------------------------------------------------
# ---               SQL-injections                     ---
# --------------------------------------------------------
def find_create_query(ast: AbstractSyntaxTreeNX):
    # found = g.V().hasLabel("ASTNode").has("kind", "CALL").where(
    #             __.out().has("kind", "NAME").has("code", "createQuery")
    #         ).valueMap().toList()
    found = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.CALL)\
        .where(
            __.out().has("kind", ASNodeKind.NAME).has("code", "createQuery")
        )\
        .nodes()

    results = []
    for f in found:
        ast_node = ast.get_node_by_id(f)
        ast_node.set_optional_property(OptionalProperties.SinkText, 'Call of method "createQuery"')
        ast_node.set_optional_property(OptionalProperties.Vulnerability, "SQL")
        ast.update_node(ast_node)
        results.append(ast_node)
    return results

def find_execute_query(ast: AbstractSyntaxTreeNX):
    # g = gremlin.g
    # found = g.V().hasLabel("ASTNode").has("kind", "CALL").where(
    #     __.and_(
    #         __.out().has("kind", "NAME").has("code", "executeQuery"),
    #         __.out().has("kind", "PARAMS")
    #     )
    # ).valueMap().toList()

    found = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.CALL)\
        .where(
            __.and_(
                __.out().has("kind", ASNodeKind.NAME).has("code", "executeQuery"),
                __.out().has("kind", ASNodeKind.PARAMS)
            )
        )\
        .nodes()

    results = []
    for f in found:
        ast_node = ast.get_node_by_id(f)
        ast_node.set_optional_property(OptionalProperties.SinkText, 'Call of method "executeQuery"')
        ast_node.set_optional_property(OptionalProperties.Vulnerability, "SQL")
        ast.update_node(ast_node)
        results.append(ast_node)
    return results

# --------------------------------------------------------
# ---                    XSS                           ---
# --------------------------------------------------------
def find_sink_by_method_qn_call(method_qn, ast: AbstractSyntaxTreeNX):
    # Пока не будет замечать, что классы могут иметь методы с одинаковыми именами
    class_name, method_name = method_qn.split(".")[-2:]
    package_name = ".".join(method_qn.split(".")[:-2])

    #g = gremlin.g
    # callNameNodes = g.V().hasLabel("ASTNode").has("kind", "ROOT").where(
    #         __.out().has("kind", "PACKAGE").has("code", packageName)
    #     ).out().has("kind", "CLASS").where(
    #         __.out().has("kind", "NAME").has("code", className)
    # ).repeat(__.out()).emit(__.has("kind", "CALL").where(
    #     __.out().has("kind", "NAME").has("code", methodName)
    # )).valueMap().toList()
    call_name_nodes = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.ROOT)\
        .where(
            __.out().has("kind", ASNodeKind.PACKAGE).has("code", package_name)
        )\
        .out()\
        .has("kind", ASNodeKind.CLASS)\
        .where(
            __.out().has("kind", ASNodeKind.NAME).has("code", class_name)
        )\
        .repeat(__.out(), max_depth=50)\
        .emit(
            __.has("kind", ASNodeKind.CALL).where(
                __.out().has("kind", ASNodeKind.NAME).has("code", method_name)
            )
        )\
        .nodes()


    results = []
    for cnn in call_name_nodes:
        ast_node = ast.get_node_by_id(cnn)
        ast_node.set_optional_property(OptionalProperties.SinkText, f'Call of method "{method_name}"')
        ast_node.set_optional_property(OptionalProperties.Vulnerability, "XSS")
        ast.update_node(ast_node)
        results.append(ast_node)

    return results

def find_sink_in_assignments(name, ast: AbstractSyntaxTreeNX):
    # assignments = gremlin.g.V().hasLabel("ASTNode").has("code", "products").where(
    #         __.repeat(__.in_()).until(__.has("kind", "ASSIGN_LEFT"))
    #     ).as_("left_part").repeat(__.in_()).until(__.has("kind", "ASSIGN")).values("optionalProperties")\
    #     .as_("right_part").select("left_part", "right_part").by(valueMap()).by().toList()

    assignments = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.ASSIGN_LEFT)\
        .as_("left_part")\
        .repeat(__.in_()).until(__.has("kind", ASNodeKind.ASSIGN))\
        .as_("right_part")\
        .select("left_part", "right_part")\
        .by(lambda q: q.nodes()[0])\
        .by(lambda q: q.valueMap()[0])

    results = []
    for assignment in assignments:
        ast_node = ast.get_node_by_id(assignment["left_part"])
        ast_node.set_optional_property(OptionalProperties.SinkText, f'Variable "{name}" assignment')
        ast_node.set_optional_property(OptionalProperties.Vulnerability, "XSS")
        ast_node.set_optional_property("assignmentExpression", assignment["right_part"]['optional_properties']["assignmentExpression"])
        ast.update_node(ast_node)
        results.append(ast_node)

    return results


def find_save_method_calls(ast: AbstractSyntaxTreeNX):
    # g = gremlin.g
    # calls = g.V().hasLabel("ASTNode").has("kind", "CALL").where(__.out().has("kind", "NAME").has("code", "save"))\
    #     .valueMap().toList()
    calls = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.CALL)\
        .where(
            __.out().has("kind", ASNodeKind.NAME).has("code", "save")
        )\
        .nodes()


    results = []
    for call in calls:
        ast_node = ast.get_node_by_id(call)
        ast_node.set_optional_property(OptionalProperties.SinkText, 'Call of method "save"')
        ast_node.set_optional_property(OptionalProperties.Vulnerability, "XSS")
        ast.update_node(ast_node)
        results.append(ast_node)

    return results

# --------------------------------------------------------
# ---               command injections                 ---
# --------------------------------------------------------
def find_exec(ast: AbstractSyntaxTreeNX):
    # g = gremlin.g
    # calls = g.V().hasLabel("ASTNode").has("kind", "CALL").where(
    #         __.out().has("kind", "NAME").has("code", "exec")
    #     ).valueMap().toList()
    calls = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.CALL)\
        .where(
            __.out().has("kind", ASNodeKind.NAME).has("code", "exec")
        )\
        .nodes()


    results = []
    for call in calls:
        ast_node = ast.get_node_by_id(call)
        ast_node.set_optional_property(OptionalProperties.SinkText, 'Call of method "exec"')
        ast_node.set_optional_property(OptionalProperties.Vulnerability, "CI")
        ast.update_node(ast_node)
        results.append(ast_node)

    return results
