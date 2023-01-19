from GremlinDriver import Gremlin
from gremlin_python.process.graph_traversal import __


def checkDFReachability(gremlin: Gremlin, sourceSharedId: str, targetSharedId: str) -> bool:
    if sourceSharedId == targetSharedId:
        return True

    g = gremlin.g
    gResp = g.V().hasLabel("DFGNode").has("sharedId", sourceSharedId).repeat(__.out().simplePath()).until(
        __.has("sharedId", targetSharedId)).toList()

    if len(gResp) > 0:
        return True
    else:
        return False


def hasTaintFlow(_taintFlowList, _taintFlow):
    source = _taintFlow["source"]
    sink = _taintFlow["sink"]
    for item in _taintFlowList:
        item_source = item["source"]
        item_sink = item["sink"]
        if source.sharedId == item_source.sharedId and sink.sharedId == item_sink.sharedId:
            return True
    return False


def deleteDuplicateTaintFlows(_taintFlows):
    newTaintFlows = []
    for tf in _taintFlows:
        if not hasTaintFlow(newTaintFlows, tf):
            newTaintFlows.append(tf)
    return newTaintFlows
