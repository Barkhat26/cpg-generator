import json
from pathlib import Path

from sqlalchemy import TypeDecorator, String


class SetAsJson(TypeDecorator):
    """Кастомный тип для хранения set в виде JSON строки"""
    impl = String

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, set):
            value = list(value)
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return set(json.loads(value))

class PathAsString(TypeDecorator):
    """Кастомный тип для хранения pathlib.Path в виде строки"""
    impl = String

    def process_bind_param(self, value, dialect):
        return str(value)

    def process_result_value(self, value, dialect):
        return Path(value)