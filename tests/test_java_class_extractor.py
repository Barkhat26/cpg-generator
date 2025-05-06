from java.java_class_extractor import JavaClassExtractor
from pathlib import Path

from storage import JavaClassesStorage


def test_extract_from_directory():
    sources_directory = Path(__file__).resolve().parent / "assets" / "zoo"
    java_classes = JavaClassExtractor.extract_from_directory(sources_directory)

    java_class_storage = JavaClassesStorage("test1", overwrite=True)
    java_class_storage.dump(list(java_classes.values()))

    loaded = java_class_storage.load()
    assert len(loaded) == 4
