from pathlib import Path


def escapeForHtml(code):
    return code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def escape_fp(filepath: Path):
    return str(filepath).replace('\\', '\\\\')

def build_method_qn(package_name: str | None, class_name: str, method_name: str) -> str:
    prefix = f'{package_name}.' if package_name else ''
    return f'{prefix}{class_name}.{method_name}'