from sqlalchemy.orm import Session
import networkx as nx

from storage.models.dfg import DFGNodeModel, DFGEdgeModel
from storage.storages.storage_base import StorageBase


class DFGStorage(StorageBase):
    @staticmethod
    def get_filename_prefix() -> str:
        return "dfg"

    def dump(self, g: nx.DiGraph):
        with Session(self.engine) as session:
            session.add_all(
                DFGNodeModel(id=node_id, **data) for node_id, data in g.nodes(data=True)
            )
            session.add_all(
                DFGEdgeModel(source=source, target=target, **data) for source, target, data in g.edges(data=True)
            )
            session.commit()

    def load(self) -> nx.Graph:
        g = nx.DiGraph()
        with Session(self.engine) as session:
            for node in session.query(DFGNodeModel):
                g.add_node(node.id,
                           line=node.line,
                           file=node.file,
                           code=node.code,
                           method=node.method,
                           shared_id=node.shared_id,
                           optional_properties=node.optional_properties
                )
            for edge in session.query(DFGEdgeModel):
                g.add_edge(edge.source, edge.target, kind=edge.kind)

        return g