from .base_checker import BaseChecker
from .injection_checker import InjectionChecker
from .xss_checker import XSSChecker
from .ci_checker import CIChecker
from ..vulnerabilitykind import VulnerabilityKind

checkers: dict[VulnerabilityKind, type[BaseChecker]] = {
    VulnerabilityKind.SQL: InjectionChecker,
    VulnerabilityKind.XSS: XSSChecker,
    VulnerabilityKind.Command: CIChecker
}
