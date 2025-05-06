from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Enum as SQLEnum

from graphs.ddg.dfg_edge import DFEdgeKind
from storage.common import Base
from storage.models.utils import SetAsJson, PathAsString


class DFGNodeModel(Base):
    __tablename__ = 'dfg_nodes'
    id = Column(Integer, primary_key=True)
    line = Column(Integer)
    file = Column(PathAsString)
    method = Column(String)
    code = Column(String)
    shared_id = Column(String)
    optional_properties = Column(JSON)
    defs = Column(SetAsJson)
    uses = Column(SetAsJson)
    self_flows = Column(SetAsJson)
    ip_defs = Column(JSON)


class DFGEdgeModel(Base):
    __tablename__ = 'dfg_edges'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Integer, ForeignKey('dfg_nodes.id'))
    target = Column(Integer, ForeignKey('dfg_nodes.id'))
    kind = Column(SQLEnum(DFEdgeKind, name="kind", native_enum=False))
    label = Column(String)
