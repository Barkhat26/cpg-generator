from enum import Enum


class WebFrameworkKind(Enum):
    struts2 = "struts2"
    spring_mvc = "spring_mvc"
    none = "none"

    @classmethod
    def from_str(cls, value: str):
        try:
            return cls(value)
        except ValueError:
            raise cls.none