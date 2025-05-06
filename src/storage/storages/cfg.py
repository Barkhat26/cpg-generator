from pathlib import Path

from sqlalchemy.orm import Session
import networkx as nx

from storage.models.cfg import CFGNodeModel, CFGEdgeModel
from storage.storages.storage_base import StorageBase


class CFGStorage(StorageBase):
    @staticmethod
    def get_filename_prefix() -> str:
        return "cfg"

    def dump(self, g: nx.DiGraph):
        with Session(self.engine) as session:
            session.add_all(
                CFGNodeModel(id=node_id, **data) for node_id, data in g.nodes(data=True)
            )
            session.add_all(
                CFGEdgeModel(source=source, target=target, **data) for source, target, data in g.edges(data=True)
            )
            session.commit()

    def load(self) -> nx.DiGraph:
        g = nx.DiGraph()
        with Session(self.engine) as session:
            for node in session.query(CFGNodeModel):
                g.add_node(node.id,
                           kind=node.kind,
                           line=node.line,
                           file=Path(node.file),
                           code=node.code,
                           method=node.method,
                           shared_id=node.shared_id,
                           optional_properties=node.optional_properties
                )
            for edge in session.query(CFGEdgeModel):
                g.add_edge(edge.source, edge.target, kind=edge.kind)

        return g

