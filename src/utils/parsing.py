from hashlib import md5
from pathlib import Path

from antlr4 import *
from antlr4.Token import CommonToken
from antlr4.tree.Tree import TerminalNodeImpl

from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser

def md5sum(s: str):
    return md5(s.encode()).hexdigest()

class SyntheticNode:
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

# TODO: переделать
def getIdByCtx(ctx, filepath: str | None = None) -> str:
    if not filepath:
        filepath = ''

    pre = f"{ctx.__class__.__name__}|{filepath}"

    if isinstance(ctx, TerminalNodeImpl):
        pre = f"{pre}|{ctx.symbol.start}|{ctx.symbol.stop}"
    elif isinstance(ctx, CommonToken):
        pre = f"{pre}|{ctx.start}|{ctx.stop}"
    elif isinstance(ctx, SyntheticNode):
        pre = f"{pre}|{ctx.start}|{ctx.stop}"
    elif isinstance(ctx, ParserRuleContext):
        pre = f"{pre}|{ctx.start.start}|{ctx.stop.stop}"
    else:
        raise Exception

    return md5sum(pre)

def getOriginalCodeText(ctx: ParserRuleContext):
    start = ctx.start.start
    stop = ctx.stop.stop
    return ctx.start.getInputStream().getText(start, stop)

def get_parse_tree_from_file(file_path: Path | str, encoding: str = "utf-8") -> JavaParser.CompilationUnitContext:
    file_stream = FileStream(file_path, encoding)
    return get_parse_tree_from_stream(file_stream)


def get_parse_tree_from_string(s: str) -> JavaParser.CompilationUnitContext:
    input_stream = InputStream(s)
    return get_parse_tree_from_stream(input_stream)

def get_parse_tree_from_stream(stream: InputStream) -> JavaParser.CompilationUnitContext:
    lexer = JavaLexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = JavaParser(tokens)
    parse_tree = parser.compilationUnit()
    return parse_tree