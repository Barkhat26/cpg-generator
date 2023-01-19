import json

from GremlinDriver import Gremlin
from gremlin_python.process.graph_traversal import __, valueMap


# --------------------------------------------------------
# ---               SQL-injections                     ---
# --------------------------------------------------------
def findCreateQuery(gremlin: Gremlin):
    g = gremlin.g
    found = g.V().hasLabel("ASTNode").has("kind", "CALL").where(
                __.out().has("kind", "NAME").has("code", "createQuery")
            ).valueMap().toList()

    results = []
    for f in found:
        astNode = gremlin.deserializeASTNode(f)
        astNode.setOptionalProperty("sinkText", f'Call of method "createQuery"')
        astNode.setOptionalProperty("vulnerability", "SQL")
        results.append(astNode)
    return results

def findExecuteQuery(gremlin: Gremlin):
    g = gremlin.g
    found = g.V().hasLabel("ASTNode").has("kind", "CALL").where(
        __.and_(
            __.out().has("kind", "NAME").has("code", "executeQuery"),
            __.out().has("kind", "PARAMS")
        )
    ).valueMap().toList()

    results = []
    for f in found:
        astNode = gremlin.deserializeASTNode(f)
        astNode.setOptionalProperty("sinkText", f'Call of method "executeQuery"')
        astNode.setOptionalProperty("vulnerability", "SQL")
        results.append(astNode)
    return results

# --------------------------------------------------------
# ---                    XSS                           ---
# --------------------------------------------------------
def findSinkByMethodQNCall(methodQN, gremlin: Gremlin):
    # Пока не будет замечать, что классы могут иметь методы с одинаковыми именами
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
        astNode.setOptionalProperty("sinkText", f'Call of method "{methodName}"')
        astNode.setOptionalProperty("vulnerability", "XSS")
        results.append(astNode)

    return results

def findSinkInAssingments(name, gremlin):
    assignments = gremlin.g.V().hasLabel("ASTNode").has("code", "products").where(
            __.repeat(__.in_()).until(__.has("kind", "ASSIGN_LEFT"))
        ).as_("left_part").repeat(__.in_()).until(__.has("kind", "ASSIGN")).values("optionalProperties")\
        .as_("right_part").select("left_part", "right_part").by(valueMap()).by().toList()

    results = []
    for assignment in assignments:
        astNode = gremlin.deserializeASTNode(assignment["left_part"])
        astNode.setOptionalProperty("sinkText", f'Variable "{name}" assignment')
        astNode.setOptionalProperty("vulnerability", "XSS")
        astNode.setOptionalProperty("assignmentExpression", json.loads(assignment["right_part"])["assignmentExpression"])
        results.append(astNode)

    return results


def findSaveMethodCalls(gremlin: Gremlin):
    g = gremlin.g
    calls = g.V().hasLabel("ASTNode").has("kind", "CALL").where(__.out().has("kind", "NAME").has("code", "save"))\
        .valueMap().toList()

    results = []
    for call in calls:
        astNode = gremlin.deserializeASTNode(call)
        astNode.setOptionalProperty("sinkText", f'Call of method "save"')
        astNode.setOptionalProperty("vulnerability", "XSS")
        results.append(astNode)

    return results

# --------------------------------------------------------
# ---               command injections                 ---
# --------------------------------------------------------
def findExec(gremlin: Gremlin):
    g = gremlin.g
    calls = g.V().hasLabel("ASTNode").has("kind", "CALL").where(
            __.out().has("kind", "NAME").has("code", "exec")
        ).valueMap().toList()

    results = []
    for call in calls:
        astNode = gremlin.deserializeASTNode(call)
        astNode.setOptionalProperty("sinkText", f'Call of method "exec"')
        astNode.setOptionalProperty("vulnerability", "CI")
        results.append(astNode)

    return results
