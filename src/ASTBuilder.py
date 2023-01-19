from antlr4 import *
import os.path
from ASTVisitor import ASTVisitor
from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser
from db import Database
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree


class ASTBuilder:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.ast = None

    def getAST(self):
        return self.ast

    def build(self, filePath) -> AbstractSyntaxTree:
        inputStream = FileStream(filePath)
        lexer = JavaLexer(inputStream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParser(tokens)
        parseTree = parser.compilationUnit()
        ast = AbstractSyntaxTree()
        ast.setProperty("filePath", filePath)
        visitor = ASTVisitor(ast)
        visitor.visit(parseTree)

        packageName = ast.getProperty("package")
        baseName = os.path.basename(os.path.splitext(filePath)[0])
        qualifiedName = f"{packageName}.{baseName}"

        for v in ast.nodes:
            v.setFile(qualifiedName)

        self.ast = ast

    def dump(self):
        db = Database(self.projectConfig)
        packageName = self.ast.getProperty("package")
        filePath = self.ast.getProperty("filePath")
        baseName = os.path.basename(os.path.splitext(filePath)[0])
        qualifiedName = f"{packageName}.{baseName}"
        db.putAST(os.path.basename(qualifiedName), self.ast)
