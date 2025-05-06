from sqlalchemy.orm import Session
import networkx as nx

from storage.models.ast import ASTNode, ASTEdge
from storage.storages.storage_base import StorageBase


class ASTStorage(StorageBase):
    @staticmethod
    def get_filename_prefix() -> str:
        return "ast"

    def dump(self, g: nx.DiGraph):
        with Session(self.engine) as session:
            session.add_all(
                ASTNode(id=node_id, **data) for node_id, data in g.nodes(data=True)
            )
            session.add_all(
                ASTEdge(source=source, target=target, **data) for source, target, data in g.edges(data=True)
            )
            session.commit()

    def load(self) -> nx.DiGraph:
        g = nx.DiGraph()
        with Session(self.engine) as session:
            for node in session.query(ASTNode):
                g.add_node(node.id,
                           kind=node.kind,
                           file=node.file,
                           line=node.line,
                           code=node.code,
                           shared_id=node.shared_id,
                           optional_properties=node.optional_properties
                )
            for edge in session.query(ASTEdge):
                g.add_edge(edge.source, edge.target, label=edge.label)

        return g

