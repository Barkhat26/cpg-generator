from antlr4 import InputStream, CommonTokenStream
from antlr.mysql.MySqlLexer import MySqlLexer
from dynamic.checkers.base_checker import BaseChecker


class InjectionChecker(BaseChecker):
    def _getNumberOfTokens(self, _query):
        input_stream = InputStream(_query.upper())
        lexer = MySqlLexer(input_stream)
        tokens = CommonTokenStream(lexer)
        return len(tokens.tokens)