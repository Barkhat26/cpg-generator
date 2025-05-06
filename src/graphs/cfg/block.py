from graphs.cfg.cfg_node import CFNode

class Block:
    def __init__(self, start: CFNode, end: CFNode, label: str = ""):
        self.start = start
        self.end = end
        self.label = label
