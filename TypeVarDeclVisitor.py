from antlr4 import *

from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from db import Database


class UserClassDeclarator:
    @staticmethod
    def checkAndDeclare(code: str, interpreter):
        inputStream = InputStream(code)
        lexer = JavaLexer(inputStream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParser(tokens)
        parseTree = parser.blockStatement()
        visitor = TypeVarDeclVisitor(interpreter)
        visitor.visit(parseTree)

class TypeVarDeclVisitor(JavaParserVisitor):
    def __init__(self, interpreter):
        self.interpreter = interpreter

    def visitLocalVariableDeclaration(self, ctx:JavaParser.LocalVariableDeclarationContext):
        # localVariableDeclaration
        #     : variableModifier* typeType variableDeclarators
        # typeType
        #     : annotation? (classOrInterfaceType | primitiveType) ('[' ']')*
        # classOrInterfaceType
        #     : IDENTIFIER typeArguments? ('.' IDENTIFIER typeArguments?)*
        #     ;
        if ctx.typeType().classOrInterfaceType() is not None:
            className = ctx.typeType().classOrInterfaceType().IDENTIFIER(0).getText()
            javaClass = Database().getJavaClassByName(className)
            if javaClass:
                self.interpreter.eval(javaClass.code)
