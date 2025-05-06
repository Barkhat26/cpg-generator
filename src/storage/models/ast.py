from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Enum as SQLEnum

from graphs.ast.ast_node import ASNodeKind
from storage.common import Base
from storage.models.utils import PathAsString


class ASTNode(Base):
    __tablename__ = 'ast_nodes'
    id = Column(Integer, primary_key=True)
    kind=Column(SQLEnum(ASNodeKind, name="kind", native_enum=False))
    line=Column(Integer)
    file=Column(PathAsString)
    code=Column(String)
    shared_id=Column(String)
    optional_properties=Column(JSON)


class ASTEdge(Base):
    __tablename__ = 'ast_edges'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Integer, ForeignKey('ast_nodes.id'))
    target = Column(Integer, ForeignKey('ast_nodes.id'))
    label = Column(String)
