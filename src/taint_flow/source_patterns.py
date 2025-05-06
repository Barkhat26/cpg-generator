from graph_dsl import Query, __
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.ast.ast_node import ASNodeKind
from optional_properties import OptionalProperties


def find_get_login(ast: AbstractSyntaxTreeNX):
    # g = gremlin.g
    # found = g.V().hasLabel("ASTNode")\
    #              .has("kind", "CALL").out()\
    #              .has("kind", "NAME").has("code", "getLogin")\
    #              .valueMap().toList()
    found = Query(ast.g)\
        .V()\
        .has("kind", ASNodeKind.CALL)\
        .out()\
        .has("kind", ASNodeKind.NAME)\
        .has("code", "getLogin")\
        .nodes()

    results = []
    for f in found:
        results.append(ast.get_node_by_id(f))

    return results


def find_source_by_method_qn_call(method_qn, ast: AbstractSyntaxTreeNX):
    class_name, method_name = method_qn.split(".")[-2:]
    package_name = ".".join(method_qn.split(".")[:-2])

    # g = gremlin.g
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
        ast_node.set_optional_property(OptionalProperties.SourceText, f'Call of method "{method_name}"')
        ast.update_node(ast_node)
        results.append(ast_node)

    return results


def find_source_in_params(name, ast: AbstractSyntaxTreeNX):
    # g = gremlin.g
    # params = g.V().hasLabel("ASTNode").has("code", name).where(
    #     __.in_().has("kind", "PARAMS")
    # ).valueMap().toList()
    params = Query(ast.g)\
        .V()\
        .has("code", name)\
        .where(
            __.in_().has("kind", ASNodeKind.PARAMS)
        )\
        .nodes()


    results = []
    for p in params:
        ast_node = ast.get_node_by_id(p)
        ast_node.set_optional_property(OptionalProperties.SourceText, f'Parameter "{name}"')
        ast.update_node(ast_node)
        results.append(ast_node)

    return results


def find_source_for_spring_mvc(class_qn, method_name, params, ast: AbstractSyntaxTreeNX):
    class_name = class_qn.split(".")[-1]
    results = []

    for param in params:
        # g.V().hasLabel("ASTNode").has("kind", "CLASS").where(
        #     __.out().has("kind", "NAME").has("code", className)
        # ).out().has("kind", "METHOD").where(
        #     __.out().has("kind", "NAME").has("code", methodName)
        # ).out().has("kind", "PARAMS").out().has("kind", "VARIABLE").where(
        #     __.out().has("kind", "NAME").has("code", param)
        # ).valueMap().toList()
        found = Query(ast.g)\
            .V()\
            .has("kind", ASNodeKind.CLASS)\
            .where(
                __.out().has("kind", ASNodeKind.NAME).has("code", class_name)
            )\
            .out().has("kind", ASNodeKind.METHOD)\
            .where(
                __.out().has("kind", ASNodeKind.NAME).has("code", method_name)
            )\
            .out().has("kind", ASNodeKind.PARAMS)\
            .out().has("kind", ASNodeKind.VARIABLE)\
            .where(
                __.out().has("kind", ASNodeKind.NAME).has("code", param)
            )\
            .nodes()

        if len(found) == 0:
            continue

        ast_node = ast.get_node_by_id(found[0])
        ast_node.set_optional_property(OptionalProperties.SourceText, f'Parameter "{param}" of method "{method_name}"')
        ast.update_node(ast_node)
        results.append(ast_node)

    return results


def find_readline(ast: AbstractSyntaxTreeNX):
    calls = Query(ast.g) \
        .V() \
        .has("kind", ASNodeKind.CALL) \
        .where(
        __.out().has("kind", ASNodeKind.NAME).has("code", "readLine")
    ) \
        .nodes()

    results = []
    for call in calls:
        ast_node = ast.get_node_by_id(call)
        ast_node.set_optional_property(OptionalProperties.SourceText, f'Call of method "readLine"')
        ast.update_node(ast_node)
        results.append(ast_node)

    return results