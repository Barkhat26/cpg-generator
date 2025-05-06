from pathlib import Path
from sqlalchemy.orm import Session

from storage.models.java_classes import JavaClassModel, JavaFieldModel, JavaMethodModel, JavaArgModel, \
    JavaAnnotationModel
from java.java_structures import JavaClass, JavaField, JavaMethod
from storage.storages.storage_base import StorageBase


class JavaClassesStorage(StorageBase):
    @staticmethod
    def get_filename_prefix() -> str:
        return "javaclasses"

    def dump(self, java_classes: list[JavaClass]):
        with Session(self.engine) as session:
            for java_class in java_classes:
                java_fields = [JavaFieldModel(
                    name=java_field.name,
                    type=java_field.type,
                    is_static=java_field.is_static,
                    modifier=java_field.modifier
                ) for java_field in java_class.fields]
                java_methods = [JavaMethodModel(
                    name=java_method.name,
                    is_static=java_method.is_static,
                    is_abstract=java_method.is_abstract,
                    modifier=java_method.modifier,
                    ret_type=java_method.ret_type,
                    args=[JavaArgModel.from_java_arg(arg) for arg in java_method.args],
                    line=java_method.line,
                    shared_id=java_method.shared_id,
                    annotations=[JavaAnnotationModel.from_java_annotation(a) for a in java_method.annotations]
                ) for java_method in java_class.methods]
                session.add(JavaClassModel(
                    name=java_class.name,
                    package=java_class.package,
                    file_path=str(java_class.filePath),
                    extends=java_class.extends,
                    imports=java_class.imports,
                    interfaces=java_class.interfaces,
                    fields=java_fields,
                    methods=java_methods,
                    type_parameters=java_class.typeParameters,
                    code=java_class.code,
                    modifiers=java_class.modifiers,
                    annotations=[JavaAnnotationModel.from_java_annotation(a) for a in java_class.annotations]
                ))
            session.commit()

    def load(self) -> list[JavaClass]:
        result: list[JavaClass] = []

        with Session(self.engine) as session:
            for java_class_model in session.query(JavaClassModel):
                result.append(JavaClass(
                    name=java_class_model.name,
                    package=java_class_model.package,
                    extends=java_class_model.extends,
                    file_path=Path(java_class_model.file_path),
                    imports=java_class_model.imports,
                    modifiers=java_class_model.modifiers,
                    annotations=java_class_model.annotations,
                    interfaces=java_class_model.interfaces,
                    fields=[JavaField(
                        name=field.name,
                        field_type=field.type,
                        is_static=field.is_static,
                        modifier=field.modifier
                    ) for field in java_class_model.fields],
                    methods=[JavaMethod(
                        name=method.name,
                        is_static=method.is_static,
                        is_abstract=method.is_abstract,
                        modifier=method.modifier,
                        ret_type=method.ret_type,
                        args=method.args,
                        line=method.line,
                        shared_id=method.shared_id,
                        annotations=method.annotations
                    ) for method in java_class_model.methods],
                    type_parameters=java_class_model.type_parameters,
                    code=java_class_model.code
                ))

        return result

