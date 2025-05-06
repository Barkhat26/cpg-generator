from antlr4 import InputStream, CommonTokenStream

from antlr.html.HTMLLexer import HTMLLexer
from dynamic.checkers.base_checker import BaseChecker


class XSSChecker(BaseChecker):
    def _getNumberOfTokens(self, _query):
        input_stream = InputStream(_query.upper())
        lexer = HTMLLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        return len(tokens.tokens)