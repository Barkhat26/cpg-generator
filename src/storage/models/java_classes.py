from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from java.java_structures import JavaArg, JavaAnnotation
from storage.common import Base
from storage.models.utils import PathAsString


class JavaFieldModel(Base):
    __tablename__ = 'java_fields'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    is_static = Column(Boolean)
    modifier = Column(String)
    java_class_id = Column(Integer, ForeignKey('java_classes.id'))

    java_class = relationship('JavaClassModel', back_populates='fields')

class JavaArgModel(Base):
    __tablename__ = 'java_args'
    id = Column(Integer, primary_key=True)
    is_final = Column(Boolean)
    type = Column(String)
    name = Column(String)
    java_method_id = Column(Integer, ForeignKey('java_methods.id'))

    java_method = relationship('JavaMethodModel', back_populates='args')
    annotations = relationship("JavaAnnotationModel", back_populates="argument")

    @staticmethod
    def from_java_arg(arg: JavaArg):
        return JavaArgModel(
            is_final=arg.is_final,
            type=arg.type,
            name=arg.name,
            annotations=[JavaAnnotationModel.from_java_annotation(a) for a in arg.annotations]
        )


class JavaAnnotationModel(Base):
    __tablename__ = 'java_annotations'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    values = Column(JSON)

    class_id = Column(Integer, ForeignKey("java_classes.id"), nullable=True)
    method_id = Column(Integer, ForeignKey("java_methods.id"), nullable=True)
    argument_id = Column(Integer, ForeignKey("java_args.id"), nullable=True)

    cls = relationship("JavaClassModel", back_populates="annotations")
    method = relationship("JavaMethodModel", back_populates="annotations")
    argument = relationship("JavaArgModel", back_populates="annotations")

    @staticmethod
    def from_java_annotation(annotation: JavaAnnotation):
        return JavaAnnotationModel(
            name=annotation.name,
            values=annotation.values
        )


class JavaMethodModel(Base):
    __tablename__ = 'java_methods'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    is_static = Column(Boolean)
    is_abstract = Column(Boolean)
    modifier = Column(String)
    ret_type = Column(String)
    line = Column(Integer)
    shared_id = Column(String)
    java_class_id = Column(Integer, ForeignKey('java_classes.id'))

    java_class = relationship('JavaClassModel', back_populates='methods')
    args = relationship('JavaArgModel', back_populates='java_method')
    annotations = relationship("JavaAnnotationModel", back_populates="method")


class JavaClassModel(Base):
    __tablename__ = 'java_classes'
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String)
    package = Column(String)
    file_path = Column(PathAsString)
    extends = Column(String)
    imports = Column(JSON)
    interfaces = Column(JSON)
    type_parameters = Column(String)
    code = Column(String)
    modifiers = Column(JSON)

    fields = relationship('JavaFieldModel', back_populates='java_class')
    methods = relationship('JavaMethodModel', back_populates='java_class')
    annotations = relationship("JavaAnnotationModel", back_populates="cls")