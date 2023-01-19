from typing import Dict

from antlr4 import *
from JavaStructures import JavaClass, JavaMethod, JavaField
from antlr.JavaLexer import JavaLexer
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from db import Database
from utils import Queue, getIdByCtx, getOriginalCodeText


class JavaClassExtractor:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.javaClasses = dict()

    def extractInfo(self, filename: str):
        inputStream = FileStream(filename)
        lexer = JavaLexer(inputStream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParser(tokens)
        parseTree = parser.compilationUnit()

        javaClasses = dict()
        visitor = JavaClassVisitor(javaClasses, filename)
        visitor.visit(parseTree)

        self.javaClasses = javaClasses

    def dump(self):
        db = Database(self.projectConfig)
        for qn, jc in self.javaClasses.items():
            db.putJavaClass(qn, jc)


class JavaClassVisitor(JavaParserVisitor):
    def __init__(self, javaClasses: Dict[str, JavaClass], filePath: str):
        self.javaClasses = javaClasses
        self.filePath = filePath
        self.packageName = ""
        self.isStatic = False
        self.isAbstract = False
        self.importsList = []
        self.activeClasses = Queue()

        self.classModifiers = []
        self.classAnnotations = []
        self.lastModifier = None
        self.lastAnnotations = []

    def visitPackageDeclaration(self, ctx:JavaParser.PackageDeclarationContext):
        # packageDeclaration: annotation* PACKAGE qualifiedName ';'
        self.packageName = ctx.qualifiedName().getText()
        return None

    def visitImportDeclaration(self, ctx:JavaParser.ImportDeclarationContext):
        # importDeclaration: IMPORT STATIC? qualifiedName ('.' '*')? ';'
        qualifiedName = ctx.qualifiedName().getText()
        last = ctx.getChildCount() - 1
        if ctx.getChild(last - 1).getText() == "*" and ctx.getChild(last - 1).getText() == ".":
            qualifiedName += "."
        self.importsList.append(qualifiedName)
        return None

    def visitAnnotation(self, ctx:JavaParser.AnnotationContext):
        # '@' qualifiedName ('(' ( elementValuePairs | elementValue )? ')')?
        #
        # elementValuePairs: elementValuePair (',' elementValuePair)*
        #
        # elementValuePair: IDENTIFIER '=' elementValue
        #
        # elementValue: expression | annotation | elementValueArrayInitializer
        qualifiedName = ctx.qualifiedName().getText()
        values = []
        if ctx.elementValue() is not None:
            values.append(ctx.elementValue().getText())
        if ctx.elementValuePairs() is not None:
            for pairCtx in ctx.elementValuePairs().elementValuePair():
                values.append(pairCtx.getText())
        return {
            "name": qualifiedName,
            "values": values
        }

    def visitTypeDeclaration(self, ctx:JavaParser.TypeDeclarationContext):
        # typeDeclaration
        #     : classOrInterfaceModifier*
        #       (classDeclaration | enumDeclaration | interfaceDeclaration | annotationTypeDeclaration)
        #     | ';'
        if ctx.classDeclaration() is not None:
            if ctx.classOrInterfaceModifier() is not None:
                # classOrInterfaceModifier: annotation
                #     | PUBLIC| PROTECTED| PRIVATE| STATIC| ABSTRACT| FINAL | STRICTFP
                self.classAnnotations = []
                self.classModifiers = []
                for modCtx in ctx.classOrInterfaceModifier():
                    if modCtx.annotation() is not None:
                        self.classAnnotations.append(self.visit(modCtx.annotation()))
                    else:
                        self.classModifiers.append(modCtx.getText())
            self.visit(ctx.classDeclaration())
        else:
            self.visitChildren(ctx)

    def visitClassDeclaration(self, ctx:JavaParser.ClassDeclarationContext):
        # classDeclaration: CLASS IDENTIFIER typeParameters? (EXTENDS typeType)? (IMPLEMENTS typeList)? classBody
        extend = None
        if ctx.typeType() is not None:
            extend = self.visit(ctx.typeType())

        implementations = []
        if ctx.typeList() is not None:
            for typeCtx in ctx.typeList().typeType():
                implementations.append(self.visit(typeCtx))

        cls = JavaClass(ctx.IDENTIFIER().getText(),
                        self.packageName,
                        extend,
                        self.filePath,
                        self.importsList,
                        modifiers=self.classModifiers,
                        annotations=self.classAnnotations)
        if ctx.typeParameters() is not None:
            cls.typeParameters = ctx.typeParameters().getText().substring(1, ctx.typeParameters().getText().length()-1).trim()

        cls.code = getOriginalCodeText(ctx)
        cls.setInterfaces(implementations)
        self.activeClasses.push(cls)
        self.visit(ctx.classBody())
        javaClass = self.activeClasses.pop()
        qualifiedName = f"{javaClass.package}.{javaClass.name}"
        self.javaClasses[qualifiedName] = javaClass
        return None

    def visitClassBodyDeclaration(self, ctx:JavaParser.ClassBodyDeclarationContext):
        # We need this only for the modifier!
        # classBodyDeclaration: ';' | STATIC? block | modifier* memberDeclaration
        #
        # modifier
        #     : classOrInterfaceModifier
        #     | NATIVE
        #     | SYNCHRONIZED
        #     | TRANSIENT
        #     | VOLATILE
        #
        # classOrInterfaceModifier
        #     : annotation
        #     | PUBLIC
        #     | PROTECTED
        #     | PRIVATE
        #     | STATIC
        #     | ABSTRACT
        #     | FINAL
        #     | STRICTFP
        if ctx.memberDeclaration() is not None:
            self.isStatic = False
            self.isAbstract = False
            self.lastModifier = None
            self.lastAnnotations = []
            if ctx.modifier() is not None:
                for cx in ctx.modifier():
                    if cx.classOrInterfaceModifier() is not None:
                        if cx.classOrInterfaceModifier().getText().startswith("public"):
                            self.lastModifier = "public"
                        elif cx.classOrInterfaceModifier().getText().startswith("private"):
                            self.lastModifier = "private"
                        elif cx.classOrInterfaceModifier().getText().startswith("protected"):
                            self.lastModifier = "protected"
                        elif cx.classOrInterfaceModifier().getText().startswith("static"):
                            self.isStatic = True
                        elif cx.classOrInterfaceModifier().getText().startswith("abstract"):
                            self.isAbstract = True
                        elif cx.classOrInterfaceModifier().annotation() is not None:
                            self.lastAnnotations.append(self.visit(cx.classOrInterfaceModifier().annotation()))
            return self.visit(ctx.memberDeclaration())
        # memberDeclaration
        #     : methodDeclaration
        #     | genericMethodDeclaration
        #     | fieldDeclaration
        #     | constructorDeclaration
        #     | genericConstructorDeclaration
        #     | interfaceDeclaration
        #     | annotationTypeDeclaration
        #     | classDeclaration
        #     | enumDeclaration
        return None

    def visitMethodDeclaration(self, ctx:JavaParser.MethodDeclarationContext):
        # methodDeclaration
        #     : typeTypeOrVoid IDENTIFIER formalParameters ('[' ']')*
        #       (THROWS qualifiedNameList)?
        #       methodBody
        # formalParameters
        #     : '(' formalParameterList? ')'
        # formalParameterList
        #     : formalParameter (',' formalParameter)* (',' lastFormalParameter)?
        #     | lastFormalParameter
        # formalParameter
        #     : variableModifier* typeType variableDeclaratorId
        # lastFormalParameter
        #     : variableModifier* typeType '...' variableDeclaratorId
        # variableDeclaratorId
        #     : IDENTIFIER ('[' ']')*
        retType = ctx.typeTypeOrVoid().getText()
        name = ctx.IDENTIFIER().getText()
        args = []
        if ctx.formalParameters().formalParameterList() is not None:
            for paramCtx in ctx.formalParameters().formalParameterList().formalParameter():
                # formalParameter: variableModifier* typeType variableDeclaratorId
                isFinal = False
                annotations = []
                for varMod in paramCtx.variableModifier():
                    # variableModifier: FINAL | annotation
                    if varMod.FINAL():
                        isFinal = True
                    else:
                        annotations.append(self.visit(varMod.annotation()))

                args.append({
                    'isFinal': isFinal,
                    'annotations': annotations,
                    'type': self.visit(paramCtx.typeType()),
                    'name': paramCtx.variableDeclaratorId().IDENTIFIER().getText()
                })
            if ctx.formalParameters().formalParameterList().lastFormalParameter() is not None:
                lfpCtx = ctx.formalParameters().formalParameterList().lastFormalParameter()
                isFinal = False
                annotations = []
                for varMod in lfpCtx.variableModifier():
                    # variableModifier: FINAL | annotation
                    if varMod.FINAL():
                        isFinal = True
                    else:
                        annotations.append(self.visit(varMod.annotation()))

                args.append({
                    'isFinal': isFinal,
                    'annotations': annotations,
                    'type': self.visit(lfpCtx.typeType()),
                    'name': lfpCtx.variableDeclaratorId().IDENTIFIER().getText()
                })
        line = ctx.start.line
        self.activeClasses.peek().addMethod(
            JavaMethod(self.lastModifier,
                       self.isStatic,
                       self.isAbstract,
                       retType,
                       name,
                       args,
                       line,
                       getIdByCtx(ctx),
                       annotations=self.lastAnnotations)
        )
        return None

    def visitConstructorDeclaration(self, ctx:JavaParser.ConstructorDeclarationContext):
        # constructorDeclaration
        #     : IDENTIFIER formalParameters (THROWS qualifiedNameList)? constructorBody=block
        retType = None
        name = ctx.IDENTIFIER().getText()
        args = []
        if ctx.formalParameters().formalParameterList() is not None:
            # formalParameterList
            #     : formalParameter (',' formalParameter)* (',' lastFormalParameter)?
            #     | lastFormalParameter
            for paramCtx in ctx.formalParameters().formalParameterList().formalParameter():
                # formalParameter: variableModifier* typeType variableDeclaratorId
                isFinal = False
                annotations = []
                for varMod in paramCtx.variableModifier():
                    # variableModifier: FINAL | annotation
                    if varMod.FINAL():
                        isFinal = True
                    else:
                        annotations.append(self.visit(varMod.annotation()))

                args.append({
                    'isFinal': isFinal,
                    'annotations': annotations,
                    'type': self.visit(paramCtx.typeType()),
                    'name': paramCtx.variableDeclaratorId().IDENTIFIER().getText()
                })
            if ctx.formalParameters().formalParameterList().lastFormalParameter() is not None:
                lfpCtx = ctx.formalParameters().formalParameterList().lastFormalParameter()
                isFinal = False
                annotations = []
                for varMod in lfpCtx.variableModifier():
                    # variableModifier: FINAL | annotation
                    if varMod.FINAL():
                        isFinal = True
                    else:
                        annotations.append(self.visit(varMod.annotation()))

                args.append({
                    'isFinal': isFinal,
                    'annotations': annotations,
                    'type': self.visit(lfpCtx.typeType()),
                    'name': lfpCtx.variableDeclaratorId().IDENTIFIER().getText()
                })
        line = ctx.start.line
        self.activeClasses.peek().addMethod(
            JavaMethod(self.lastModifier,
                       self.isStatic,
                       self.isAbstract,
                       retType,
                       name,
                       args,
                       line,
                       getIdByCtx(ctx),
                       annotations=self.lastAnnotations)
        )
        return None

    def visitFieldDeclaration(self, ctx:JavaParser.FieldDeclarationContext):
        # fieldDeclaration: typeType variableDeclarators ';'
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?
        # variableDeclaratorId: IDENTIFIER ('[' ']')*
        for varCtx in ctx.variableDeclarators().variableDeclarator():
            name = varCtx.variableDeclaratorId().IDENTIFIER().getText()
            fieldType = self.visit(ctx.typeType())
            idx = varCtx.variableDeclaratorId().getText().find("[")
            if idx > 0:
                fieldType += varCtx.variableDeclaratorId().getText()[idx:]
            self.activeClasses.peek().addField(JavaField(self.lastModifier, self.isStatic, fieldType, name))

    def visitTypeType(self, ctx:JavaParser.TypeTypeContext):
        # typeType
        #     : annotation? (classOrInterfaceType | primitiveType) ('[' ']')*
        return ctx.getText()

    def visitEnumDeclaration(self, ctx:JavaParser.EnumDeclarationContext):
        # Just ignore enums for now ...
        return None

    def visitInterfaceDeclaration(self, ctx:JavaParser.InterfaceDeclarationContext):
        # Just ignore interfaces for now ...
        return None

