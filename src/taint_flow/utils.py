from graph_dsl import Query, __
from graphs.ddg.data_flow_graph_nx import DataFlowGraphNX
from taint_flow.taintflow import TaintFlow


def check_df_reachability(dfg: DataFlowGraphNX, source_shared_id: str, target_shared_id: str) -> bool:
    if source_shared_id == target_shared_id:
        return True

    # g = gremlin.g
    # gResp = g.V().hasLabel("DFGNode").has("sharedId", sourceSharedId).repeat(__.out().simplePath()).until(
    #     __.has("sharedId", targetSharedId)).toList()
    g_resp = Query(dfg.g)\
        .V()\
        .has("shared_id", source_shared_id)\
        .repeat(__.out().simplePath(), max_depth=50)\
        .until(__.has("shared_id", target_shared_id))\
        .nodes()

    if len(g_resp) > 0:
        return True

    return False


def has_taint_flow(taint_flow_list: list[TaintFlow], taint_flow: TaintFlow):
    source = taint_flow.source
    sink = taint_flow.sink

    for item in taint_flow_list:
        item_source = item.source
        item_sink = item.sink

        if source.shared_id == item_source.shared_id and sink.shared_id == item_sink.shared_id:
            return True

    return False


def delete_duplicate_taint_flows(taint_flows: list[TaintFlow]) -> list[TaintFlow]:
    new_taint_flows = []

    for tf in taint_flows:
        if not has_taint_flow(new_taint_flows, tf):
            new_taint_flows.append(tf)

    return new_taint_flows
