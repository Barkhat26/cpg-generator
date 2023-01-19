from graphs.cfg.CFNode import CFNode


class ASEdge:
    def __init__(self, source: CFNode, label: str, target: CFNode):
        self.source = source
        self.label = label
        self.target = target
