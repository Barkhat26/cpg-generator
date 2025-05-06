from graphs.ast.ast_node import ASNode


class ASEdge:
    def __init__(self, source: ASNode, target: ASNode, label: str | None = None):
        self.source = source
        self.target = target
        self.label = label
