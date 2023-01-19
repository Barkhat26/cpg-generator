class Node:
    def __init__(self):
        self.Id = None

class Edge:
    def __init__(self, source: Node, label: str, target: Node):
        self.source = source
        self.label = label
        self.target = target


class Digraph:
    def __init__(self):
        self.nodes = list()
        self.entry_node = None
        self.allEdges = list()
        self.inEdges = dict()
        self.outEdges = dict()

    def addVertex(self, node: Node):
        node.Id = 1 if self.size() == 0 else (self.nodes[-1].Id + 1)
        self.nodes.append(node)
        self.inEdges[node.Id] = list()
        self.outEdges[node.Id] = list()

    def addEdge(self, e: Edge):
        if e not in self.allEdges:
            self.allEdges.append(e)
            self.inEdges.get(e.target.Id).append(e)
            self.outEdges.get(e.source.Id).append(e)

    def removeVertex(self, nodeId: int):
        vertex = [v for v in self.nodes if v.Id == nodeId]
        if len(vertex) > 0:
            vertex = vertex[0]
            self.nodes.remove(vertex)
            inEdges = self.inEdges[nodeId]
            outEdges = self.outEdges[nodeId]
            # for e in list(set(inEdges) | set(outEdges)):
            #     self.allEdges.remove(e)
            for e in inEdges:
                if e in self.allEdges:
                    self.allEdges.remove(e)
            for e in outEdges:
                if e in self.allEdges:
                    self.allEdges.remove(e)
            del self.inEdges[nodeId]
            del self.outEdges[nodeId]

    def outNodes(self, n: Node):
        return [e.target for e in self.outEdges.get(n.Id)]

    def inNodes(self, n: Node):
        return [e.source for e in self.inEdges.get(n.Id)]

    def getOutDegree(self, v: Node):
        return len(self.outEdges.get(v.Id))

    def getInDegree(self, v: Node):
        return len(self.inEdges.get(v.Id))

    def size(self):
        return len(self.nodes)