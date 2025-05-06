from graphs.ddg.dfg_node import DFNode


class TaintFlow:
    def __init__(self, source: DFNode, vulnerability: str, sink: DFNode):
        self.source = source
        self.vulnerability = vulnerability
        self.sink = sink

    def __str__(self):
        return f'taint [{self.vulnerability}]: {self.source.code} -> {self.sink.code}'