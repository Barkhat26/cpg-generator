from GremlinDriver import Gremlin
from graphs.ast.ASNode import ASNode, ASNodeKind
from gremlin_python.process.graph_traversal import __


def findGetLogin(gremlin):
    g = gremlin.g
    found = g.V().hasLabel("ASTNode")\
                 .has("kind", "CALL").out()\
                 .has("kind", "NAME").has("code", "getLogin")\
                 .valueMap().toList()

    results = []
    for f in found:
        results.append(gremlin.deserializeASTNode(f))

    return results


def findSourceByMethodQNCall(methodQN, gremlin: Gremlin):
    className, methodName = methodQN.split(".")[-2:]
    packageName = ".".join(methodQN.split(".")[:-2])
    g = gremlin.g

    callNameNodes = g.V().hasLabel("ASTNode").has("kind", "ROOT").where(
            __.out().has("kind", "PACKAGE").has("code", packageName)
        ).out().has("kind", "CLASS").where(
            __.out().has("kind", "NAME").has("code", className)
    ).repeat(__.out()).emit(__.has("kind", "CALL").where(
        __.out().has("kind", "NAME").has("code", methodName)
    )).valueMap().toList()

    results = []
    for cnn in callNameNodes:
        astNode = gremlin.deserializeASTNode(cnn)
        astNode.setOptionalProperty("sourceText", f'Call of method "{methodName}"')
        results.append(astNode)

    return results


def findSourceInParams(name, gremlin):
    g = gremlin.g
    params = g.V().hasLabel("ASTNode").has("code", name).where(
        __.in_().has("kind", "PARAMS")
    ).valueMap().toList()

    results = []
    for p in params:
        astNode = gremlin.deserializeASTNode(p)
        astNode.setOptionalProperty("sourceText", f'Parameter "{name}"')
        results.append(astNode)

    return results


def findSourceForSpringMVC(classQN, methodName, params, gremlin):
    className = classQN.split(".")[-1]
    g = gremlin.g
    results = []
    for param in params:
        gResp = g.V().hasLabel("ASTNode").has("kind", "CLASS").where(
                    __.out().has("kind", "NAME").has("code", className)
                ).out().has("kind", "METHOD").where(
                    __.out().has("kind", "NAME").has("code", methodName)
                ).out().has("kind", "PARAMS").out().has("kind", "VARIABLE").where(
                    __.out().has("kind", "NAME").has("code", param)
                ).valueMap().toList()

        if len(gResp) == 0:
            continue

        gResp = gResp[0]
        astNode = gremlin.deserializeASTNode(gResp)
        astNode.setOptionalProperty("sourceText", f'Parameter "{param}" of method "{methodName}"')
        results.append(astNode)

    return results
