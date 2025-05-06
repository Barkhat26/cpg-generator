from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Enum as SQLEnum

from graphs.cfg.cfg_node import CFNodeKind
from graphs.cfg.cfg_edge import CFEdgeKind
from storage.common import Base
from storage.models.utils import PathAsString


class CFGNodeModel(Base):
    __tablename__ = 'cfg_nodes'
    id = Column(Integer, primary_key=True)
    kind=Column(SQLEnum(CFNodeKind, name="kind", native_enum=False))
    line=Column(Integer)
    file=Column(PathAsString)
    method=Column(String)
    code=Column(String)
    shared_id=Column(String)
    optional_properties=Column(JSON)


class CFGEdgeModel(Base):
    __tablename__ = 'cfg_edges'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Integer, ForeignKey('cfg_nodes.id'))
    target = Column(Integer, ForeignKey('cfg_nodes.id'))
    kind = Column(SQLEnum(CFEdgeKind, name="kind", native_enum=False))