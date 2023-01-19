from antlr4 import *
from ASTVisitor import ASTVisitor
from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor


class TypeDeterminator:
    @staticmethod
    def checkIsBuiltin(_type):
        inputStream = InputStream(_type)
        lexer = JavaLexer(inputStream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParser(tokens)
        parseTree = parser.typeType()

        visitor = TypeVisitor()
        visitor.visit(parseTree)
        return visitor.isBuiltin


BUILTIN_TYPES = [
    # Primitive type wrappers
    "Boolean",
    "Character",
    "Byte",
    "Short",
    "Integer",
    "Long",
    "Float",
    "Double",
    # Collections
    "List",
    "Queue",
    "Deque",
    "Set",
    "SortedSet",
    "NavigableSet",
    "Map",
    "ArrayList",
    "LinkedList",
    "ArrayDeque",
    "HashSet",
    "TreeSet",
    "LinkedHashSet",
    "PriorityQueue",
    "HashMap",
    "TreeMap",
]

class TypeVisitor(JavaParserVisitor):
    def __init__(self):
        self.visitedClassOrInterfaceType = False
        self.isBuiltin = False

    def visitClassOrInterfaceType(self, ctx:JavaParser.ClassOrInterfaceTypeContext):
        if not self.visitedClassOrInterfaceType:
            identifier = ctx.IDENTIFIER(0).getText()
            if identifier in BUILTIN_TYPES:
                self.isBuiltin = True
            self.visitedClassOrInterfaceType = True

