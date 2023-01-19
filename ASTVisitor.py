from antlr4 import ParserRuleContext
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from graphs.ast.ASNode import ASNode, ASNodeKind
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.digraph import Edge
from utils import Stack, getOriginalCodeText


class ASTVisitor(JavaParserVisitor):
    def __init__(self, ast: AbstractSyntaxTree):
        self.ast = ast
        self.parentStack = Stack()
        self.ast.getRoot().setCode("Filename")
        self.parentStack.push(self.ast.getRoot())
        self.typeModifier = ""
        self.memberModifier = ""
        self.vars = dict()
        self.varsCounter = 0

    # ************************************************************
    # ***                  DECLARATIONS                        ***
    # ************************************************************

    def visitPackageDeclaration(self, ctx: JavaParser.PackageDeclarationContext):
        # packageDeclaration: annotation* PACKAGE qualifiedName ';'
        self.ast.setProperty("package", ctx.qualifiedName().getText())
        packageNode = ASNode(ASNodeKind.PACKAGE)
        packageNode.setCode(ctx.qualifiedName().getText())
        packageNode.setLineOfCode(ctx.start.line)
        packageNode.setSharedId(ctx)
        self.ast.addVertex(packageNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, packageNode))

    def visitImportDeclaration(self, ctx: JavaParser.ImportDeclarationContext):
        # importDeclaration: IMPORT STATIC? qualifiedName ('.' '*')? ';'
        qualifiedName = ctx.qualifiedName().getText()
        last = ctx.getChildCount() - 1
        if ctx.getText()[last - 1] == "*" and ctx.getText()[last - 2] == ".":
            qualifiedName += ".*"
        importNode = ASNode(ASNodeKind.IMPORT)
        importNode.setCode(qualifiedName)
        importNode.setLineOfCode(ctx.start.line)
        importNode.setSharedId(ctx)
        self.ast.addVertex(importNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, importNode))

    def visitTypeDeclaration(self, ctx: JavaParser.TypeDeclarationContext):
        # typeDeclaration
        #     : classOrInterfaceModifier*
        #       (classDeclaration | enumDeclaration | interfaceDeclaration | annotationTypeDeclaration)
        #     | ';'
        self.typeModifier = ""
        for modifierCtx in ctx.classOrInterfaceModifier():
            self.typeModifier += modifierCtx.getText() + " "
        self.typeModifier = self.typeModifier.rstrip()
        self.visitChildren(ctx)

    def visitClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        # classDeclaration
        #     : CLASS IDENTIFIER typeParameters?
        #       (EXTENDS typeType)?
        #       (IMPLEMENTS typeList)?
        #       classBody
        classNode = ASNode(ASNodeKind.CLASS)
        classNode.setLineOfCode(ctx.start.line)
        classNode.setSharedId(ctx)
        self.ast.addVertex(classNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, classNode))

        modifierNode = ASNode(ASNodeKind.MODIFIER)
        modifierNode.setLineOfCode(ctx.start.line)
        modifierNode.setCode(self.typeModifier)
        self.ast.addVertex(modifierNode)
        self.ast.addEdge(Edge(classNode, None, modifierNode))

        nameNode = ASNode(ASNodeKind.NAME)
        nameNode.setLineOfCode(ctx.start.line)
        nameNode.setCode(ctx.IDENTIFIER().getText())
        self.ast.addVertex(nameNode)
        self.ast.addEdge(Edge(classNode, None, nameNode))

        if ctx.typeType() is not None:
            extendsNode = ASNode(ASNodeKind.EXTENDS)
            extendsNode.setLineOfCode(ctx.typeType().start.line)
            extendsNode.setCode(ctx.typeType().getText())
            extendsNode.setSharedId(ctx.typeType())
            self.ast.addVertex(extendsNode)
            self.ast.addEdge(Edge(classNode, None, extendsNode))

        if ctx.typeList() is not None:
            implementsNode = ASNode(ASNodeKind.IMPLEMENTS)
            implementsNode.setLineOfCode(ctx.typeList().start.line)
            implementsNode.setSharedId(ctx.typeList())
            self.ast.addVertex(implementsNode)
            self.ast.addEdge(Edge(classNode, None, implementsNode))
            for typeCtx in ctx.typeList().typeType():
                interfaceNode = ASNode(ASNodeKind.INTERFACE)
                interfaceNode.setLineOfCode(typeCtx.start.line)
                interfaceNode.setCode(typeCtx.getText())
                interfaceNode.setSharedId(typeCtx)
                self.ast.addVertex(interfaceNode)
                self.ast.addEdge(Edge(implementsNode, None, interfaceNode))

        self.parentStack.push(classNode)
        self.visit(ctx.classBody())
        self.parentStack.pop()

    def visitClassBodyDeclaration(self, ctx: JavaParser.ClassBodyDeclarationContext):
        # classBodyDeclaration
        #     : ';'
        #     | STATIC? block
        #     | modifier* memberDeclaration
        #
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

        if ctx.block() is not None:
            staticBlock = ASNode(ASNodeKind.STATIC_BLOCK)
            staticBlock.setLineOfCode(ctx.block().start.line)
            staticBlock.setSharedId(ctx.block())
            self.ast.addVertex(staticBlock)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, staticBlock))
            self.parentStack.push(staticBlock)
            self.visitChildren(ctx.block())
            self.parentStack.pop()
        elif ctx.memberDeclaration() is not None:
            self.memberModifier = ""
            for modCtx in ctx.modifier():
                self.memberModifier += modCtx.getText() + " "
            self.memberModifier = self.memberModifier.rstrip()

            if ctx.memberDeclaration().fieldDeclaration() is not None:
                fieldNode = ASNode(ASNodeKind.FIELD)
                fieldNode.setLineOfCode(ctx.memberDeclaration().fieldDeclaration().start.line)
                fieldNode.setSharedId(ctx.memberDeclaration().fieldDeclaration())
                self.ast.addVertex(fieldNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, fieldNode))
                self.parentStack.push(fieldNode)
                self.visit(ctx.memberDeclaration().fieldDeclaration())
                self.parentStack.pop()
            elif ctx.memberDeclaration().constructorDeclaration() is not None:
                constructorNode = ASNode(ASNodeKind.CONSTRUCTOR)
                constructorNode.setLineOfCode(ctx.memberDeclaration().constructorDeclaration().start.line)
                constructorNode.setSharedId(ctx.memberDeclaration().constructorDeclaration())
                self.ast.addVertex(constructorNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, constructorNode))
                self.parentStack.push(constructorNode)
                self.visit(ctx.memberDeclaration().constructorDeclaration())
                self.parentStack.pop()
            elif ctx.memberDeclaration().methodDeclaration() is not None:
                methodNode = ASNode(ASNodeKind.METHOD)
                methodNode.setLineOfCode(ctx.memberDeclaration().methodDeclaration().start.line)
                methodNode.setSharedId(ctx.memberDeclaration().methodDeclaration())
                self.ast.addVertex(methodNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, methodNode))
                self.parentStack.push(methodNode)
                self.visit(ctx.memberDeclaration().methodDeclaration())
                self.parentStack.pop()
            else:
                self.visitChildren(ctx.memberDeclaration())

    def visitConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
        # constructorDeclaration
        #     : IDENTIFIER formalParameters (THROWS qualifiedNameList)? constructorBody=block

        modifierNode = ASNode(ASNodeKind.MODIFIER)
        modifierNode.setLineOfCode(ctx.start.line)
        modifierNode.setCode(self.memberModifier)
        self.ast.addVertex(modifierNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, modifierNode))

        if ctx.formalParameters().formalParameterList() is not None:
            paramsNode = ASNode(ASNodeKind.PARAMS)
            paramsNode.setLineOfCode(ctx.formalParameters().formalParameterList().start.line)
            paramsNode.setSharedId(ctx.formalParameters().formalParameterList())
            self.ast.addVertex(paramsNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, paramsNode))
            self.parentStack.push(paramsNode)

            for paramCtx in ctx.formalParameters().formalParameterList().formalParameter():
                varNode = ASNode(ASNodeKind.VARIABLE)
                varNode.setLineOfCode(paramCtx.start.line)
                varNode.setSharedId(paramCtx)
                self.ast.addVertex(varNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, varNode))

                typeNode = ASNode(ASNodeKind.TYPE)
                typeNode.setLineOfCode(paramCtx.typeType().start.line)
                typeNode.setCode(paramCtx.typeType().getText())
                typeNode.setSharedId(paramCtx.typeType())
                self.ast.addVertex(typeNode)
                self.ast.addEdge(Edge(varNode, None, typeNode))

                nameNode = ASNode(ASNodeKind.NAME)
                nameNode.setLineOfCode(paramCtx.variableDeclaratorId().start.line)
                nameNode.setCode(paramCtx.variableDeclaratorId().getText())
                nameNode.setSharedId(paramCtx.variableDeclaratorId())
                self.ast.addVertex(nameNode)
                self.ast.addEdge(Edge(varNode, None, nameNode))

            if ctx.formalParameters().formalParameterList().lastFormalParameter() is not None:
                lfpCtx = ctx.formalParameters().formalParameterList().lastFormalParameter()
                varNode = ASNode(ASNodeKind.VARIABLE)
                varNode.setLineOfCode(lfpCtx.start.line)
                varNode.setSharedId(lfpCtx)
                self.ast.addVertex(varNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, varNode))

                typeNode = ASNode(ASNodeKind.TYPE)
                typeNode.setLineOfCode(lfpCtx.typeType().start.line)
                typeNode.setCode(lfpCtx.typeType().getText())
                typeNode.setSharedId(lfpCtx.typeType())
                self.ast.addVertex(typeNode)
                self.ast.addEdge(Edge(varNode, None, typeNode))

                nameNode = ASNode(ASNodeKind.NAME)
                nameNode.setLineOfCode(lfpCtx.variableDeclaratorId().start.line)
                nameNode.setCode(lfpCtx.variableDeclaratorId().getText())
                nameNode.setSharedId(lfpCtx.variableDeclaratorId())
                self.ast.addVertex(nameNode)
                self.ast.addEdge(Edge(varNode, None, nameNode))

            self.parentStack.pop()

        bodyBlock = ASNode(ASNodeKind.BLOCK)
        bodyBlock.setLineOfCode(ctx.constructorBody.start.line)
        bodyBlock.setSharedId(ctx.constructorBody)
        self.ast.addVertex(bodyBlock)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, bodyBlock))
        self.parentStack.push(bodyBlock)
        self.visitChildren(ctx.constructorBody)
        self.parentStack.pop()
        self.resetLocalVars()

    def visitFieldDeclaration(self, ctx: JavaParser.FieldDeclarationContext):
        # fieldDeclaration: typeType variableDeclarators ';'
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?
        for varCtx in ctx.variableDeclarators().variableDeclarator():
            modifierNode = ASNode(ASNodeKind.MODIFIER)
            modifierNode.setLineOfCode(ctx.start.line)
            modifierNode.setCode(self.memberModifier)
            self.ast.addVertex(modifierNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, modifierNode))

            typeNode = ASNode(ASNodeKind.TYPE)
            typeNode.setLineOfCode(ctx.typeType().start.line)
            typeNode.setCode(ctx.typeType().getText())
            typeNode.setSharedId(ctx.typeType())
            self.ast.addVertex(typeNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, typeNode))

            nameNode = ASNode(ASNodeKind.NAME)
            nameNode.setLineOfCode(varCtx.variableDeclaratorId().start.line)
            nameNode.setCode(varCtx.variableDeclaratorId().getText())
            nameNode.setSharedId(varCtx.variableDeclaratorId())
            self.ast.addVertex(nameNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, nameNode))

            if varCtx.variableInitializer() is not None:
                initNode = ASNode(ASNodeKind.INIT_VALUE)
                initNode.setLineOfCode(varCtx.variableInitializer().start.line)
                initNode.setCode("=")
                initNode.setSharedId(varCtx.variableInitializer())
                self.ast.addVertex(initNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, initNode))
                self.parentStack.push(initNode)
                self.visit(varCtx.variableInitializer())
                self.parentStack.pop()

    def visitMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        # methodDeclaration
        #     : typeTypeOrVoid IDENTIFIER formalParameters ('[' ']')*
        #       (THROWS qualifiedNameList)?
        #       methodBody
        #
        # formalParameters: '(' formalParameterList? ')'
        #
        # formalParameterList
        #     : formalParameter (',' formalParameter)* (',' lastFormalParameter)?
        #     | lastFormalParameter
        #
        # formalParameter: variableModifier* typeType variableDeclaratorId
        #
        # lastFormalParameter: variableModifier* typeType '...' variableDeclaratorId

        modifierNode = ASNode(ASNodeKind.MODIFIER)
        modifierNode.setLineOfCode(ctx.start.line)
        modifierNode.setCode(self.memberModifier)
        self.ast.addVertex(modifierNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, modifierNode))

        retNode = ASNode(ASNodeKind.RET_VAL_TYPE)
        retNode.setLineOfCode(ctx.start.line)
        retNode.setCode(ctx.typeTypeOrVoid().getText())
        retNode.setSharedId(ctx.typeTypeOrVoid())
        self.ast.addVertex(retNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, retNode))

        nameNode = ASNode(ASNodeKind.NAME)
        nameNode.setLineOfCode(ctx.start.line)
        nameNode.setCode(ctx.IDENTIFIER().getText())
        self.ast.addVertex(nameNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, nameNode))

        if ctx.formalParameters().formalParameterList() is not None:
            paramsNode = ASNode(ASNodeKind.PARAMS)
            paramsNode.setLineOfCode(ctx.formalParameters().formalParameterList().start.line)
            paramsNode.setSharedId(ctx.formalParameters().formalParameterList())
            self.ast.addVertex(paramsNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, paramsNode))
            self.parentStack.push(paramsNode)

            for paramCtx in ctx.formalParameters().formalParameterList().formalParameter():
                varNode = ASNode(ASNodeKind.VARIABLE)
                varNode.setLineOfCode(paramCtx.start.line)
                varNode.setSharedId(paramCtx)
                self.ast.addVertex(varNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, varNode))

                typeNode = ASNode(ASNodeKind.TYPE)
                typeNode.setLineOfCode(paramCtx.typeType().start.line)
                typeNode.setCode(paramCtx.typeType().getText())
                typeNode.setSharedId(paramCtx.typeType())
                self.ast.addVertex(typeNode)
                self.ast.addEdge(Edge(varNode, None, typeNode))

                nameNode = ASNode(ASNodeKind.NAME)
                nameNode.setLineOfCode(paramCtx.variableDeclaratorId().start.line)
                nameNode.setCode(paramCtx.variableDeclaratorId().getText())
                nameNode.setSharedId(paramCtx.variableDeclaratorId())
                self.ast.addVertex(nameNode)
                self.ast.addEdge(Edge(varNode, None, nameNode))

            if ctx.formalParameters().formalParameterList().lastFormalParameter() is not None:
                lfpCtx = ctx.formalParameters().formalParameterList().lastFormalParameter()
                varNode = ASNode(ASNodeKind.VARIABLE)
                varNode.setLineOfCode(lfpCtx.start.line)
                varNode.setSharedId(lfpCtx)
                self.ast.addVertex(varNode)
                self.ast.addEdge(Edge(self.parentStack.peek(), None, varNode))

                typeNode = ASNode(ASNodeKind.TYPE)
                typeNode.setLineOfCode(lfpCtx.typeType().start.line)
                typeNode.setCode(lfpCtx.typeType().getText())
                typeNode.setSharedId(lfpCtx.typeType())
                self.ast.addVertex(typeNode)
                self.ast.addEdge(Edge(varNode, None, typeNode))

                nameNode = ASNode(ASNodeKind.NAME)
                nameNode.setLineOfCode(lfpCtx.variableDeclaratorId().start.line)
                nameNode.setCode(lfpCtx.variableDeclaratorId().getText())
                nameNode.setSharedId(lfpCtx.variableDeclaratorId())
                self.ast.addVertex(nameNode)
                self.ast.addEdge(Edge(varNode, None, nameNode))

            self.parentStack.pop()

        if ctx.methodBody().block() is not None:
            bodyBlock = ASNode(ASNodeKind.BLOCK)
            bodyBlock.setLineOfCode(ctx.methodBody().block().start.line)
            bodyBlock.setSharedId(ctx.methodBody().block())
            self.ast.addVertex(bodyBlock)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, bodyBlock))
            self.parentStack.push(bodyBlock)
            self.visitChildren(ctx.methodBody().block())
            self.parentStack.pop()
            self.resetLocalVars()

    def visitLocalVariableDeclaration(self, ctx: JavaParser.LocalVariableDeclarationContext):
        # localVariableDeclaration: variableModifier* typeType variableDeclarators
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?

        for varCtx in ctx.variableDeclarators().variableDeclarator():
            varNode = ASNode(ASNodeKind.VARIABLE)
            varNode.setLineOfCode(varCtx.start.line)
            varNode.setSharedId(varCtx)
            self.ast.addVertex(varNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, varNode))

            typeNode = ASNode(ASNodeKind.TYPE)
            typeNode.setLineOfCode(ctx.typeType().start.line)
            typeNode.setCode(ctx.typeType().getText())
            typeNode.setSharedId(ctx.typeType())
            self.ast.addVertex(typeNode)
            self.ast.addEdge(Edge(varNode, None, typeNode))

            nameNode = ASNode(ASNodeKind.NAME)
            nameNode.setLineOfCode(varCtx.variableDeclaratorId().start.line)
            nameNode.setCode(varCtx.variableDeclaratorId().getText())
            nameNode.setSharedId(varCtx.variableDeclaratorId())
            self.ast.addVertex(nameNode)
            self.ast.addEdge(Edge(varNode, None, nameNode))

            if varCtx.variableInitializer() is not None:
                initNode = ASNode(ASNodeKind.INIT_VALUE)
                initNode.setLineOfCode(varCtx.variableInitializer().start.line)
                initNode.setCode("=")
                initNode.setSharedId(varCtx.variableInitializer())
                self.ast.addVertex(initNode)
                self.ast.addEdge(Edge(varNode, None, initNode))
                self.parentStack.push(initNode)
                self.visit(varCtx.variableInitializer())
                self.parentStack.pop()

    # *******************************************************************
    # ***                     STATEMENTS                              ***
    # *******************************************************************

    def visitStatement(self, ctx: ParserRuleContext, normalized: str):
        stmtNode = ASNode(ASNodeKind.STATEMENT)
        stmtNode.setLineOfCode(ctx.start.line)
        stmtNode.setCode(getOriginalCodeText(ctx))
        stmtNode.setSharedId(ctx)
        self.ast.addVertex(stmtNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, stmtNode))

    def visitStmtExpr(self, ctx: JavaParser.StmtExprContext):
        # statement: statementExpression=expression ';'
        stmtNode = ASNode(ASNodeKind.STATEMENT)
        stmtNode.setLineOfCode(ctx.start.line)
        stmtNode.setSharedId(ctx)
        self.ast.addVertex(stmtNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, stmtNode))
        self.parentStack.push(stmtNode)
        self.visit(ctx.expression())
        self.parentStack.pop()

    def visitStmtBreak(self, ctx: JavaParser.StmtBreakContext):
        # statement: BREAK IDENTIFIER? ';'
        if ctx.IDENTIFIER() is None:
            self.visitStatement(ctx, None)
        else:
            self.visitStatement(ctx, "break $LABEL")

    def visitStmtContinue(self, ctx: JavaParser.StmtContinueContext):
        # statement: CONTINUE IDENTIFIER? ';'
        if ctx.IDENTIFIER() is None:
            self.visitStatement(ctx, None)
        else:
            self.visitStatement(ctx, "continue $LABEL")

    def visitStmtReturn(self, ctx: JavaParser.StmtReturnContext):
        # statement: RETURN expression? ';'
        if ctx.expression() is None:
            self.visitStatement(ctx, None)
        else:
            # self.visitStatement(ctx, "return " + self.visit(ctx.expression()))
            retNode = ASNode(ASNodeKind.RETURN)
            retNode.setLineOfCode(ctx.start.line)
            retNode.setSharedId(ctx)
            self.ast.addVertex(retNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, retNode))
            self.parentStack.push(retNode)
            self.visit(ctx.expression())
            self.parentStack.pop()


    def visitStmtThrow(self, ctx: JavaParser.StmtThrowContext):
        # statement: THROW expression ';'
        self.visitStatement(ctx, "throw " + self.visit(ctx.expression()))

    def visitStmtSynchronized(self, ctx: JavaParser.StmtSynchronizedContext):
        # statement: SYNCHRONIZED parExpression block
        synchNode = ASNode(ASNodeKind.SYNC)
        synchNode.setLineOfCode(ctx.start.line)
        synchNode.setSharedId(ctx)
        self.ast.addVertex(synchNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, synchNode))

        self.parentStack.push(synchNode)
        self.visitStatement(ctx.parExpression().expression(), self.visit(ctx.parExpression().expression()))
        self.parentStack.pop()

        block = ASNode(ASNodeKind.BLOCK)
        block.setLineOfCode(ctx.block().start.line)
        block.setSharedId(ctx.block())
        self.ast.addVertex(block)
        self.ast.addEdge(Edge(synchNode, block))
        self.parentStack.push(block)
        self.visit(ctx.block())
        self.parentStack.pop()

    def visitStmtLabel(self, ctx: JavaParser.StmtLabelContext):
        # statement: identifierLabel=IDENTIFIER ':' statement
        labelNode = ASNode(ASNodeKind.LABELED)
        labelNode.setLineOfCode(ctx.start.line)
        labelNode.setSharedId(ctx)
        self.ast.addVertex(labelNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, labelNode))

        nameNode = ASNode(ASNodeKind.NAME)
        nameNode.setCode(ctx.IDENTIFIER().getText())
        nameNode.setLineOfCode(ctx.start.line)
        nameNode.setSharedId(ctx.IDENTIFIER())
        self.ast.addVertex(nameNode)
        self.ast.addEdge(Edge(labelNode, None, nameNode))

        self.parentStack.push(labelNode)
        self.visit(ctx.statement())
        self.parentStack.pop()

    def visitStmtIf(self, ctx: JavaParser.StmtIfContext):
        # statement: IF parExpression trueClause=statement (ELSE falseClause=statement)?
        ifNode = ASNode(ASNodeKind.IF)
        ifNode.setLineOfCode(ctx.start.line)
        ifNode.setSharedId(ctx)
        self.ast.addVertex(ifNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, ifNode))

        condNode = ASNode(ASNodeKind.CONDITION)
        condNode.setLineOfCode(ctx.parExpression().start.line)
        condNode.setSharedId(ctx.parExpression())
        self.ast.addVertex(condNode)
        self.ast.addEdge(Edge(ifNode, None, condNode))
        self.parentStack.push(condNode)
        self.visit(ctx.parExpression())
        self.parentStack.pop()

        thenNode = ASNode(ASNodeKind.THEN)
        thenNode.setLineOfCode(ctx.trueClause.start.line)
        thenNode.setSharedId(ctx.trueClause)
        self.ast.addVertex(thenNode)
        self.ast.addEdge(Edge(ifNode, None, thenNode))
        self.parentStack.push(thenNode)
        self.visit(ctx.trueClause)
        self.parentStack.pop()

        if ctx.falseClause is not None:
            elseNode = ASNode(ASNodeKind.ELSE)
            elseNode.setLineOfCode(ctx.falseClause.start.line)
            elseNode.setSharedId(ctx.falseClause)
            self.ast.addVertex(elseNode)
            self.ast.addEdge(Edge(ifNode, None, elseNode))
            self.parentStack.push(elseNode)
            self.visit(ctx.falseClause)
            self.parentStack.pop()

    def visitStmtFor(self, ctx: JavaParser.StmtForContext):
        # statement: FOR '(' forControl ')' statement
        # forControl
        #     : enhancedForControl
        #     | forInit? ';' expression? ';' forUpdate=expressionList?
        # enhancedForControl
        #     : variableModifier* typeType variableDeclaratorId ':' expression
        # forInit
        #     : localVariableDeclaration
        #     | expressionList

        if ctx.forControl().enhancedForControl() is not None:
            forNode = ASNode(ASNodeKind.FOR_EACH)
            forNode.setLineOfCode(ctx.start.line)
            forNode.setSharedId(ctx)
            self.ast.addVertex(forNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, forNode))

            varType = ASNode(ASNodeKind.TYPE)
            varType.setLineOfCode(ctx.forControl().enhancedForControl().typeType().start.line)
            varType.setCode(ctx.forControl().enhancedForControl().typeType().getText())
            varType.setSharedId(ctx.forControl().enhancedForControl().typeType())
            self.ast.addVertex(varType)
            self.ast.addEdge(Edge(forNode, None, varType))

            varID = ASNode(ASNodeKind.NAME)
            varID.setLineOfCode(ctx.forControl().enhancedForControl().variableDeclaratorId().start.line)
            varID.setCode(ctx.forControl().enhancedForControl().variableDeclaratorId().getText())
            varID.setSharedId(ctx.forControl().enhancedForControl().variableDeclaratorId())
            self.ast.addVertex(varID)
            self.ast.addEdge(Edge(forNode, None, varID))

            inNode = ASNode(ASNodeKind.FOR_IN)
            inNode.setLineOfCode(ctx.forControl().enhancedForControl().expression().start.line)
            # inNode.setCode(getOriginalCodeText(ctx.forControl().enhancedForControl().expression()))
            # inNode.setSharedId(ctx.forControl().enhancedForControl().expression())
            self.ast.addVertex(inNode)
            self.ast.addEdge(Edge(forNode, None, inNode))
            self.parentStack.push(inNode)
            self.visit(ctx.forControl().enhancedForControl().expression())
            self.parentStack.pop()
        else:
            forNode = ASNode(ASNodeKind.FOR)
            forNode.setLineOfCode(ctx.start.line)
            forNode.setSharedId(ctx)
            self.ast.addVertex(forNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, forNode))

            if ctx.forControl().forInit() is not None:
                forInit = ASNode(ASNodeKind.FOR_INIT)
                forInit.setLineOfCode(ctx.forControl().forInit().start.line)
                forInit.setSharedId(ctx.forControl().forInit())
                self.ast.addVertex(forInit)
                self.ast.addEdge(Edge(forNode, None, forInit))
                if ctx.forControl().forInit().localVariableDeclaration() is not None:
                    self.parentStack.push(forInit)
                    self.visit(ctx.forControl().forInit().localVariableDeclaration())
                    self.parentStack.pop()
                else:
                    expr = ASNode(ASNodeKind.STATEMENT)
                    expr.setLineOfCode(ctx.forControl().forInit().expressionList().expression(0).start.line)
                    expr.setCode(getOriginalCodeText(ctx.forControl().forInit().expressionList().expression(0)))
                    expr.setSharedId(ctx.forControl().forInit().expressionList().expression(0))
                    self.ast.addVertex(expr)
                    self.ast.addEdge(Edge(forInit, None, expr))

                    for exprCtx in ctx.forControl().forInit().expressionList().expression()[1:]:
                        expr = ASNode(ASNodeKind.STATEMENT)
                        expr.setLineOfCode(exprCtx.start.line)
                        expr.setCode(getOriginalCodeText(exprCtx))
                        expr.setSharedId(exprCtx)
                        self.ast.addVertex(expr)
                        self.ast.addEdge(Edge(forInit, None, expr))

            if ctx.forControl().expression() is not None:
                forExpr = ASNode(ASNodeKind.CONDITION)
                forExpr.setLineOfCode(ctx.forControl().expression().start.line)
                forExpr.setSharedId(ctx.forControl().expression())
                self.ast.addVertex(forExpr)
                self.ast.addEdge(Edge(forNode, None, forExpr))
                self.parentStack.push(forExpr)
                self.visit(ctx.forControl().expression())
                self.parentStack.pop()

            if ctx.forControl().forUpdate is not None:
                forUpdate = ASNode(ASNodeKind.FOR_UPDATE)
                forUpdate.setLineOfCode(ctx.forControl().forUpdate.start.line)
                forUpdate.setSharedId(ctx.forControl().forUpdate)
                self.ast.addVertex(forUpdate)
                self.ast.addEdge(Edge(forNode, None, forUpdate))

                expr = ASNode(ASNodeKind.STATEMENT)
                expr.setLineOfCode(ctx.forControl().forUpdate.expression(0).start.line)
                expr.setSharedId(ctx.forControl().forUpdate.expression(0))
                self.ast.addVertex(expr)
                self.ast.addEdge(Edge(forUpdate, None, expr))
                self.parentStack.push(expr)
                self.visit(ctx.forControl().forUpdate.expression(0))
                self.parentStack.pop()

                for exprCtx in ctx.forControl().forUpdate.expression()[1:]:
                    expr = ASNode(ASNodeKind.STATEMENT)
                    expr.setLineOfCode(exprCtx.start.line)
                    expr.setCode(getOriginalCodeText(exprCtx))
                    expr.setSharedId(exprCtx)
                    self.ast.addVertex(expr)
                    self.ast.addEdge(Edge(forUpdate, None, expr))
                    self.parentStack.push(expr)
                    self.visit(exprCtx)
                    self.parentStack.pop()

        block = ASNode(ASNodeKind.BLOCK)
        block.setLineOfCode(ctx.statement().start.line)
        block.setSharedId(ctx.statement())
        self.ast.addVertex(block)
        self.ast.addEdge(Edge(forNode, None, block))
        self.parentStack.push(block)
        self.visit(ctx.statement())
        self.parentStack.pop()

    def visitStmtWhile(self, ctx: JavaParser.StmtWhileContext):
        # statement: WHILE parExpression statement
        whileNode = ASNode(ASNodeKind.WHILE)
        whileNode.setLineOfCode(ctx.start.line)
        whileNode.setSharedId(ctx)
        self.ast.addVertex(whileNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, whileNode))

        condNode = ASNode(ASNodeKind.CONDITION)
        condNode.setLineOfCode(ctx.parExpression().expression().start.line)
        condNode.setSharedId(ctx.parExpression().expression())
        self.ast.addVertex(condNode)
        self.ast.addEdge(Edge(whileNode, None, condNode))
        self.parentStack.push(condNode)
        self.visit(ctx.parExpression().expression())
        self.parentStack.pop()

        block = ASNode(ASNodeKind.BLOCK)
        block.setLineOfCode(ctx.statement().start.line)
        block.setSharedId(ctx.statement())
        self.ast.addVertex(block)
        self.ast.addEdge(Edge(whileNode, None, block))
        self.parentStack.push(block)
        self.visit(ctx.statement())
        self.parentStack.pop()

    def visitStmtDoWhile(self, ctx: JavaParser.StmtDoWhileContext):
        # statement: DO statement WHILE parExpression ';'
        doWhileNode = ASNode(ASNodeKind.DO_WHILE)
        doWhileNode.setLineOfCode(ctx.start.line)
        doWhileNode.setSharedId(ctx)
        self.ast.addVertex(doWhileNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, doWhileNode))

        condNode = ASNode(ASNodeKind.CONDITION)
        condNode.setLineOfCode(ctx.parExpression().expression().start.line)
        condNode.setCode(getOriginalCodeText(ctx.parExpression().expression()))
        condNode.setSharedId(ctx.parExpression().expression())
        self.ast.addVertex(condNode)
        self.ast.addEdge(Edge(doWhileNode, None, condNode))

        block = ASNode(ASNodeKind.BLOCK)
        block.setLineOfCode(ctx.statement().start.line)
        block.setSharedId(ctx.statement())
        self.ast.addVertex(block)
        self.ast.addEdge(Edge(doWhileNode, None, block))
        self.parentStack.push(block)
        self.visit(ctx.statement())
        self.parentStack.pop()

    def visitStmtTry(self, ctx: JavaParser.StmtTryContext):
        # statement: TRY block (catchClause+ finallyBlock? | finallyBlock)
        tryNode = ASNode(ASNodeKind.TRY)
        tryNode.setLineOfCode(ctx.start.line)
        tryNode.setSharedId(ctx)
        self.ast.addVertex(tryNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, tryNode))

        tryBlock = ASNode(ASNodeKind.BLOCK)
        tryBlock.setLineOfCode(ctx.block().start.line)
        tryBlock.setSharedId(ctx.block())
        self.ast.addVertex(tryBlock)
        self.ast.addEdge(Edge(tryNode, None, tryBlock))
        self.parentStack.push(tryBlock)
        self.visit(ctx.block())
        self.parentStack.pop()

        if ctx.catchClause() is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            for catchCtx in ctx.catchClause():
                catchNode = ASNode(ASNodeKind.CATCH)
                catchNode.setLineOfCode(catchCtx.start.line)
                catchNode.setSharedId(catchCtx)
                self.ast.addVertex(catchNode)
                self.ast.addEdge(Edge(tryNode, None, catchNode))

                catchType = ASNode(ASNodeKind.TYPE)
                catchType.setLineOfCode(catchCtx.catchType().start.line)
                catchType.setCode(catchCtx.catchType().getText())
                catchType.setSharedId(catchCtx.catchType())
                self.ast.addVertex(catchType)
                self.ast.addEdge(Edge(catchNode, None, catchType))

                catchName = ASNode(ASNodeKind.NAME)
                catchName.setCode(catchCtx.IDENTIFIER().getText())
                catchName.setSharedId(catchCtx.IDENTIFIER())
                self.ast.addVertex(catchName)
                self.ast.addEdge(Edge(catchNode, None, catchName))

                catchBlock = ASNode(ASNodeKind.BLOCK)
                catchBlock.setLineOfCode(catchCtx.block().start.line)
                catchBlock.setSharedId(catchCtx.block())
                self.ast.addVertex(catchBlock)
                self.ast.addEdge(Edge(catchNode, None, catchBlock))
                self.parentStack.push(catchBlock)
                self.visit(catchCtx.block())
                self.parentStack.pop()

        if ctx.finallyBlock() is not None:
            # finallyBlock: FINALLY block
            finallyNode = ASNode(ASNodeKind.FINALLY)
            finallyNode.setLineOfCode(ctx.finallyBlock().start.line)
            finallyNode.setSharedId(ctx.finallyBlock())
            self.ast.addVertex(finallyNode)
            self.ast.addEdge(Edge(tryNode, None, finallyNode))
            self.parentStack.push(finallyNode)
            self.visit(ctx.finallyBlock().block())
            self.parentStack.pop()

    def visitStmtTryResource(self, ctx: JavaParser.StmtTryResourceContext):
        # statement: TRY resourceSpecification block catchClause* finallyBlock?
        # resourceSpecification: '(' resources ';'? ')'
        # resources: resource (';' resource)*
        # resource: variableModifier* classOrInterfaceType variableDeclaratorId '=' expression

        tryNode = ASNode(ASNodeKind.TRY)
        tryNode.setLineOfCode(ctx.start.line)
        tryNode.setSharedId(ctx)
        self.ast.addVertex(tryNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, tryNode))

        resNode = ASNode(ASNodeKind.RESOURCES)
        resNode.setLineOfCode(ctx.resourceSpecification().start.line)
        resNode.setSharedId(ctx.resourceSpecification())
        self.ast.addVertex(resNode)
        self.ast.addEdge(Edge(tryNode, None, resNode))

        for resCtx in ctx.resourceSpecification().resources().resource():
            varNode = ASNode(ASNodeKind.VARIABLE)
            varNode.setLineOfCode(resCtx.start.line)
            varNode.setSharedId(resCtx)
            self.ast.addVertex(varNode)
            self.ast.addEdge(Edge(resNode, None, varNode))

            resType = ASNode(ASNodeKind.TYPE)
            resType.setLineOfCode(resCtx.classOrInterfaceType().start.line)
            resType.setCode(resCtx.classOrInterfaceType().getText())
            resType.setSharedId(resCtx.classOrInterfaceType())
            self.ast.addVertex(resType)
            self.ast.addEdge(Edge(resNode, None, resType))

            resName = ASNode(ASNodeKind.NAME)
            resName.setLineOfCode(resCtx.variableDeclaratorId().start.line)
            resName.setCode(resCtx.variableDeclaratorId().getText())
            resName.setSharedId(resCtx.variableDeclaratorId())
            self.ast.addVertex(resName)
            self.ast.addEdge(Edge(resNode, None, resName))

            resInit = ASNode(ASNodeKind.INIT_VALUE)
            resInit.setLineOfCode(resCtx.expression().start.line)
            resInit.setSharedId(resCtx)
            self.ast.addVertex(resInit)
            self.ast.addEdge(Edge(resNode, None, resInit))
            self.parentStack.push(resInit)
            self.visit(resCtx.expression())
            self.parentStack.pop()

        tryBlock = ASNode(ASNodeKind.BLOCK)
        tryBlock.setLineOfCode(ctx.block().start.line)
        tryBlock.setSharedId(ctx.block())
        self.ast.addVertex(tryBlock)
        self.ast.addEdge(Edge(tryNode, None, tryBlock))
        self.parentStack.push(tryBlock)
        self.visit(ctx.block())
        self.parentStack.pop()

        if ctx.catchClause() is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            for catchCtx in ctx.catchClause():
                catchNode = ASNode(ASNodeKind.CATCH)
                catchNode.setLineOfCode(catchCtx.start.line)
                catchNode.setSharedId(catchCtx)
                self.ast.addVertex(catchNode)
                self.ast.addEdge(Edge(tryNode, None, catchNode))

                catchType = ASNode(ASNodeKind.TYPE)
                catchType.setLineOfCode(catchCtx.catchType().start.line)
                catchType.setCode(catchCtx.catchType().getText())
                catchType.setSharedId(catchCtx.catchType())
                self.ast.addVertex(catchType)
                self.ast.addEdge(Edge(catchNode, None, catchType))

                catchName = ASNode(ASNodeKind.NAME)
                catchName.setLineOfCode(catchCtx.IDENTIFIER().symbol.line)
                catchName.setCode(catchCtx.IDENTIFIER().getText())
                catchName.setSharedId(catchCtx.IDENTIFIER())
                self.ast.addVertex(catchName)
                self.ast.addEdge(Edge(catchNode, None, catchName))

                catchBlock = ASNode(ASNodeKind.BLOCK)
                catchBlock.setLineOfCode(catchCtx.block().start.line)
                catchBlock.setSharedId(catchCtx.block())
                self.ast.addVertex(catchBlock)
                self.ast.addEdge(Edge(catchNode, None, catchBlock))
                self.parentStack.push(catchBlock)
                self.visit(catchCtx.block())
                self.parentStack.pop()

        if ctx.finallyBlock() is not None:
            # finallyBlock: FINALLY block
            finallyNode = ASNode(ASNodeKind.FINALLY)
            finallyNode.setLineOfCode(ctx.finallyBlock().start.line)
            finallyNode.setSharedId(ctx.finallyBlock())
            self.ast.addVertex(finallyNode)
            self.ast.addEdge(Edge(tryNode, None, finallyNode))
            self.parentStack.push(finallyNode)
            self.visit(ctx.finallyBlock().block())
            self.parentStack.pop()

    def visitStmtSwitch(self, ctx: JavaParser.StmtSwitchContext):
        # statement: SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'
        # switchBlockStatementGroup: switchLabel+ blockStatement+
        # switchLabel
        #     : CASE (constantExpression=expression | enumConstantName=IDENTIFIER) ':'
        #     | DEFAULT ':'

        switchNode = ASNode(ASNodeKind.SWITCH)
        switchNode.setLineOfCode(ctx.start.line)
        switchNode.setSharedId(ctx)
        self.ast.addVertex(switchNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, switchNode))

        varName = ASNode(ASNodeKind.NAME)
        varName.setLineOfCode(ctx.parExpression().expression().start.line)
        varName.setCode(ctx.parExpression().expression().getText())
        varName.setSharedId(ctx.parExpression().expression())
        self.ast.addVertex(varName)
        self.ast.addEdge(Edge(switchNode, None, varName))

        if ctx.switchBlockStatementGroup() is not None:
            for groupCtx in ctx.switchBlockStatementGroup():
                blockNode = ASNode(ASNodeKind.BLOCK)
                blockNode.setLineOfCode(groupCtx.blockStatement(0).start.line)
                blockNode.setSharedId(groupCtx.blockStatement(0))
                self.ast.addVertex(blockNode)
                self.parentStack.push(blockNode)
                for lblCtx in ctx.switchBlockStatementGroup().switchLabel():
                    self.visit(lblCtx)
                for stmtCtx in ctx.switchBlockStatementGroup().blockStatement():
                    self.visit(stmtCtx)
                self.parentStack.pop()

        if ctx.switchLabel() is not None:
            self.parentStack.push(switchNode)
            for lblCtx in ctx.switchLabel():
                self.visit(lblCtx)
            self.parentStack.pop()

    def visitSwitchLabel(self, ctx: JavaParser.SwitchLabelContext):
        # switchLabel
        #     : CASE (constantExpression=expression | enumConstantName=IDENTIFIER) ':'
        #     | DEFAULT ':'
        if ctx.constantExpression() is not None:
            caseNode = ASNode(ASNodeKind.CASE)
            caseNode.setLineOfCode(ctx.constantExpression().start.line)
        elif ctx.enumConstantName() is not None:
            caseNode = ASNode(ASNodeKind.CASE)
            caseNode.setLineOfCode(ctx.enumConstantName().start.line)
        else:
            caseNode = ASNode(ASNodeKind.DEFAULT)
            caseNode.setLineOfCode(ctx.start.line)

        caseNode.setSharedId(ctx)
        self.ast.addVertex(caseNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, caseNode))

    # *******************************************************************
    # ***                        EXPRESSIONS                          ***
    # ********************************************************************

    def visitExprPrimary(self, ctx: JavaParser.ExprPrimaryContext):
        # expression: primary             # ExprPrimary
        # primary
        #     : '(' expression ')'
        #     | THIS
        #     | SUPER
        #     | literal
        #     | IDENTIFIER
        #     | typeTypeOrVoid '.' CLASS
        #     | nonWildcardTypeArguments (explicitGenericInvocationSuffix | THIS arguments)
        primary = ctx.primary()
        if primary.expression() is not None:
            # return "(" + self.visit(primary.expression()) + ")"
            self.visit(primary.expression())
        if primary.IDENTIFIER() is not None:
            idNode = ASNode(ASNodeKind.NAME)
            idNode.setLineOfCode(primary.start.line)
            idNode.setCode(primary.IDENTIFIER().getText())
            idNode.setSharedId(primary.IDENTIFIER())
            self.ast.addVertex(idNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, idNode))
        if primary.THIS() is not None:
            thisNode = ASNode(ASNodeKind.NAME)
            thisNode.setLineOfCode(primary.start.line)
            thisNode.setCode("this")
            thisNode.setSharedId(primary.THIS())
            self.ast.addVertex(thisNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, thisNode))
        if primary.nonWildcardTypeArguments() is not None:
            if primary.arguments() is not None:
                return getOriginalCodeText(primary.nonWildcardTypeArguments()) \
                       + "this" + self.visit(primary.arguments())
            else:
                if primary.explicitGenericInvocationSuffix().IDENTIFIER() is not None:
                    suffix = primary.explicitGenericInvocationSuffix().IDENTIFIER().getText() + \
                             self.visit(primary.explicitGenericInvocationSuffix().arguments())
                else:
                    suffix = "super" + self.visit(primary.explicitGenericInvocationSuffix().superSuffix())
                return getOriginalCodeText(primary.nonWildcardTypeArguments()) + suffix
        if primary.literal() is not None:
            literalNode = ASNode(ASNodeKind.LITERAL)
            literalNode.setLineOfCode(primary.literal().start.line)
            literalNode.setCode(primary.literal().getText())
            literalNode.setSharedId(primary.literal())
            self.ast.addVertex(literalNode)
            self.ast.addEdge(Edge(self.parentStack.peek(), None, literalNode))
            return None
        return getOriginalCodeText(primary)

    def visitExprDot(self, ctx: JavaParser.ExprDotContext):
        # expression: expression bop='.'
        #       ( IDENTIFIER
        #       | methodCall
        #       | THIS
        #       | NEW nonWildcardTypeArguments? innerCreator
        #       | SUPER superSuffix
        #       | explicitGenericInvocation
        #       )                 # ExprDot
        dotNode = ASNode(ASNodeKind.DOT)
        dotNode.setLineOfCode(ctx.start.line)
        dotNode.setSharedId(ctx)
        self.ast.addVertex(dotNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, dotNode))
        self.parentStack.push(dotNode)
        self.visit(ctx.expression())
        self.parentStack.pop()
        if ctx.IDENTIFIER() is not None:
            idNode = ASNode(ASNodeKind.NAME)
            idNode.setLineOfCode(ctx.start.line)
            idNode.setCode(ctx.IDENTIFIER().getText())
            idNode.setSharedId(ctx.IDENTIFIER())
            self.ast.addVertex(idNode)
            self.ast.addEdge(Edge(dotNode, None, idNode))
        if ctx.THIS() is not None:
            # return self.visit(ctx.expression()) + ".this"
            thisNode = ASNode(ASNodeKind.NAME)
            thisNode.setLineOfCode(ctx.start.line)
            thisNode.setCode("this")
            thisNode.setSharedId(ctx.THIS())
            self.ast.addVertex(thisNode)
            self.ast.addEdge(Edge(dotNode, None, thisNode))
        if ctx.NEW() is not None:
            return self.visit(ctx.expression()) + ".new " + getOriginalCodeText(ctx.nonWildcardTypeArguments()) \
                   + ctx.innerCreator().IDENTIFIER().getText() \
                   + getOriginalCodeText(ctx.innerCreator().nonWildcardTypeArgumentsOrDiamond()) \
                   + self.visit(ctx.innerCreator().classCreatorRest().arguments()) \
                   + self.visit(ctx.innerCreator().classCreatorRest().classBody())
        if ctx.SUPER() is not None:
            return self.visit(ctx.expression()) + ".super" + self.visit(ctx.superSuffix())
        if ctx.methodCall() is not None:
            self.parentStack.push(dotNode)
            self.visit(ctx.methodCall())
            self.parentStack.pop()
        if ctx.explicitGenericInvocation() is not None:
            if ctx.explicitGenericInvocation().explicitGenericInvocationSuffix().IDENTIFIER() is not None:
                suffix = ctx.explicitGenericInvocation().explicitGenericInvocationSuffix().IDENTIFIER().getText() \
                         + self.visit(ctx.explicitGenericInvocation().explicitGenericInvocationSuffix().arguments())
            else:
                suffix = "super" + self.visit(
                    ctx.explicitGenericInvocation().explicitGenericInvocationSuffix().superSuffix()
                )

            return self.visit(ctx.expression()) + "." \
                   + getOriginalCodeText(ctx.explicitGenericInvocation().nonWildcardTypeArguments()) \
                   + suffix

    def visitSuperSuffix(self, ctx: JavaParser.SuperSuffixContext):
        # superSuffix
        #     : arguments
        #     | '.' IDENTIFIER arguments?
        superSuffix = ""
        if ctx.IDENTIFIER() is not None:
            superSuffix = "." + ctx.IDENTIFIER().getText()
        if ctx.arguments() is not None:
            superSuffix += self.visit(ctx.arguments())
        return superSuffix

    def visitArguments(self, ctx: JavaParser.ArgumentsContext):
        # arguments
        #     : '(' expressionList? ')'
        argsNode = ASNode(ASNodeKind.ARGS)
        argsNode.setLineOfCode(ctx.start.line)
        argsNode.setSharedId(ctx)
        self.ast.addVertex(argsNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, argsNode))
        # if ctx.expressionList() is None:
        #     return "()"
        # return "(" + self.visit(ctx.expressionList()) + ")"
        if ctx.expressionList() is not None:
            self.parentStack.push(argsNode)
            self.visit(ctx.expressionList())
            self.parentStack.pop()

    def visitExprArray(self, ctx: JavaParser.ExprArrayContext):
        # expression '[' expression ']'                    # ExprArray
        node = ASNode(ASNodeKind.ARRAY)
        node.setLineOfCode(ctx.start.line)
        node.setSharedId(ctx)
        self.ast.addVertex(node)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, node))
        self.parentStack.push(node)
        self.visit(ctx.expression(0))
        self.visit(ctx.expression(1))
        self.parentStack.pop()

    # def visitExprMethodCall(self, ctx: JavaParser.ExprMethodCallContext):
    #     # expression: methodCall                                       # ExprMethodCall
    #
    #     methodCall = ctx.methodCall()
    #     if methodCall.IDENTIFIER() is not None:
    #         firstPart = methodCall.IDENTIFIER().getText()
    #     elif methodCall.THIS() is not None:
    #         firstPart = "this"
    #     else:
    #         firstPart = "super"
    #
    #     nameNode = ASNode(ASNodeKind.NAME)
    #     nameNode.setLineOfCode(ctx.start.line)
    #     nameNode.setCode(firstPart)
    #     self.ast.addVertex(nameNode)
    #     self.ast.addEdge(Edge(self.parentStack.peek(), None, nameNode))
    #
    #     if methodCall.expressionList():
    #         paramsNode = ASNode(ASNodeKind.PARAMS)
    #         paramsNode.setLineOfCode(methodCall.expressionList().start.line)
    #         self.ast.addVertex(paramsNode)
    #         self.ast.addEdge(Edge(self.parentStack.peek(), None, paramsNode))
    #         self.parentStack.push(paramsNode)
    #         self.visit(methodCall.expressionList())
    #         self.parentStack.pop()
    #
    #     return None

    def visitMethodCall(self, ctx:JavaParser.MethodCallContext):
        # methodCall
        #     : IDENTIFIER '(' expressionList? ')'
        #     | THIS '(' expressionList? ')'
        #     | SUPER '(' expressionList? ')'
        if ctx.IDENTIFIER() is not None:
            firstPart = ctx.IDENTIFIER().getText()
        elif ctx.THIS() is not None:
            firstPart = "this"
        else:
            firstPart = "super"

        callNode = ASNode(ASNodeKind.CALL)
        callNode.setLineOfCode(ctx.start.line)
        callNode.setSharedId(ctx)
        callNode.setOptionalProperty("name", firstPart)
        self.ast.addVertex(callNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, callNode))

        nameNode = ASNode(ASNodeKind.NAME)
        nameNode.setLineOfCode(ctx.start.line)
        nameNode.setCode(firstPart)
        nameNode.setSharedId(ctx.getChild(0))
        self.ast.addVertex(nameNode)
        self.ast.addEdge(Edge(callNode, None, nameNode))

        if ctx.expressionList():
            # Bad code. It is needed for taint-flow analysis
            args = []
            for exprCtx in ctx.expressionList().expression():
                args.append(getOriginalCodeText(exprCtx))
            callNode.setOptionalProperty("args", args)

            paramsNode = ASNode(ASNodeKind.PARAMS)
            paramsNode.setLineOfCode(ctx.expressionList().start.line)
            paramsNode.setSharedId(ctx.expressionList())
            self.ast.addVertex(paramsNode)
            self.ast.addEdge(Edge(callNode, None, paramsNode))
            self.parentStack.push(paramsNode)
            self.visit(ctx.expressionList())
            self.parentStack.pop()

        return None

    def visitExprNew(self, ctx: JavaParser.ExprNewContext):
        # expression: NEW creator                                      # ExprNew
        # creator
        #     : nonWildcardTypeArguments createdName classCreatorRest
        #     | createdName (arrayCreatorRest | classCreatorRest)

        return self.visitChildren(ctx)

    def visitExprCasting(self, ctx: JavaParser.ExprCastingContext):
        # '(' typeType ')' expression                      # ExprCasting
        castNode = ASNode(ASNodeKind.CAST)
        castNode.setLineOfCode(ctx.start.line)
        castNode.setSharedId(ctx)
        self.ast.addVertex(castNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, castNode))

        typeNode = ASNode(ASNodeKind.TYPE)
        typeNode.setLineOfCode(ctx.typeType().start.line)
        typeNode.setCode(getOriginalCodeText(ctx.typeType()))
        typeNode.setSharedId(ctx.typeType())
        self.ast.addVertex(typeNode)
        self.ast.addEdge(Edge(castNode, None, typeNode))

        self.parentStack.push(castNode)
        self.visit(ctx.expression())
        self.parentStack.peek()

        # return "(" + getOriginalCodeText(ctx.typeType()) + ") " + self.visit(ctx.expression())

    def visitExprPostUnaryOp(self, ctx: JavaParser.ExprPostUnaryOpContext):
        # expression postfix=('++' | '--')                 # ExprPostUnaryOp
        node = ASNode(ASNodeKind.UNARY)
        node.setLineOfCode(ctx.start.line)
        node.setCode(ctx.postfix.text)
        node.setSharedId(ctx)
        self.ast.addVertex(node)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, node))
        self.parentStack.push(node)
        self.visit(ctx.expression())
        self.parentStack.pop()
        # return self.visit(ctx.expression()) + ctx.postfix.text

    def visitExprPrePreUnaryOp(self, ctx: JavaParser.ExprPrePreUnaryOpContext):
        # prefix=('+'|'-'|'++'|'--') expression            # ExprPrePreUnaryOp
        self.visitUnaryExpression(ctx)
        # return ctx.prefix.text + self.visit(ctx.expression())

    def visitExprNegation(self, ctx: JavaParser.ExprNegationContext):
        # prefix=('~'|'!') expression                      # ExprNegation
        self.visitUnaryExpression(ctx)
        # return ctx.prefix.text + self.visit(ctx.expression())

    def visitExprMulDivMod(self, ctx: JavaParser.ExprMulDivModContext):
        # expression bop=('*'|'/'|'%') expression          # ExprMulDivMod
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    def visitUnaryExpression(self, opCtx, opText=None):
        opNode = ASNode(ASNodeKind.UNARY)
        opNode.setLineOfCode(opCtx.start.line)
        if opText is None:
            opNode.setCode(opCtx.prefix.text)
        else:
            opNode.setCode(opText)
        opNode.setSharedId(opCtx)
        self.ast.addVertex(opNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, opNode))
        self.parentStack.push(opNode)
        self.visit(opCtx.expression())
        self.parentStack.pop()

    def visitBinaryExpression(self, opCtx, opText=None):
        opNode = ASNode(ASNodeKind.BOP)
        opNode.setLineOfCode(opCtx.start.line)
        if opText is None:
            opNode.setCode(opCtx.bop.text)
        else:
            opNode.setCode(opText)
        opNode.setSharedId(opCtx)
        self.ast.addVertex(opNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, opNode))
        self.parentStack.push(opNode)
        leftExpr = opCtx.expression(0)
        rightExpr = opCtx.expression(1)
        self.visit(leftExpr)
        self.visit(rightExpr)
        self.parentStack.pop()

    def visitExprAddSub(self, ctx: JavaParser.ExprAddSubContext):
        # expression bop=('+'|'-') expression              # ExprAddSub

        # addSubNode = ASNode(ASNodeKind.ARITH)
        # addSubNode.setLineOfCode(ctx.start.line)
        # addSubNode.setCode(ctx.bop.text)
        # addSubNode.setSharedId(ctx)
        # self.ast.addVertex(addSubNode)
        # self.ast.addEdge(Edge(self.parentStack.peek(), None, addSubNode))
        # self.parentStack.push(addSubNode)
        # self.visit(ctx.expression(0))
        # self.visit(ctx.expression(1))
        # self.parentStack.pop()
        self.visitBinaryExpression(ctx)

    def visitExprBitShift(self, ctx: JavaParser.ExprBitShiftContext):
        # expression ('<' '<' | '>' '>' '>' | '>' '>') expression
        sub = ctx.getText()[len(ctx.getChild(0).getText())]
        if sub.startswith(">>>"):
            bop = ">>>"
        else:
            bop = sub[:2]
        self.visitBinaryExpression(ctx, opText=bop)

    def visitExprComparison(self, ctx: JavaParser.ExprComparisonContext):
        # expression bop=('<=' | '>=' | '>' | '<') expression
        # opNode = ASNode(ASNodeKind.BOP)
        # opNode.setLineOfCode(ctx.start.line)
        # opNode.setCode(ctx.bop.text)
        # opNode.setSharedId(ctx)
        # self.ast.addVertex(opNode)
        # self.ast.addEdge(Edge(self.parentStack.peek(), None, opNode))
        # self.parentStack.push(opNode)
        # self.visit(ctx.expression(0))
        # self.visit(ctx.expression(1))
        # self.parentStack.pop()
        self.visitBinaryExpression(ctx)

    def visitExprInstanceOf(self, ctx: JavaParser.ExprInstanceOfContext):
        # expression bop=INSTANCEOF typeType
        # return self.visit(ctx.expression(0)) + " instanceof " + getOriginalCodeText(ctx.typeType())
        self.visitBinaryExpression(ctx)

    def visitExprEquality(self, ctx: JavaParser.ExprEqualityContext):
        # expression bop=('==' | '!=') expression
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    def visitExprBitAnd(self, ctx: JavaParser.ExprBitAndContext):
        # expression bop='&' expression
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    def visitExprBitXor(self, ctx: JavaParser.ExprBitXorContext):
        # expression bop='^' expression
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    def visitExprBitOr(self, ctx: JavaParser.ExprBitOrContext):
        # expression bop='|' expression
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    def visitExprLogicAnd(self, ctx: JavaParser.ExprLogicAndContext):
        # expression bop='&&' expression
        # opNode = ASNode(ASNodeKind.BOP)
        # opNode.setLineOfCode(ctx.start.line)
        # opNode.setCode(ctx.bop.text)
        # opNode.setSharedId(ctx)
        # self.ast.addVertex(opNode)
        # self.ast.addEdge(Edge(self.parentStack.peek(), None, opNode))
        # self.parentStack.push(opNode)
        # self.visit(ctx.expression(0))
        # self.visit(ctx.expression(1))
        # self.parentStack.pop()
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    def visitExprLogicOr(self, ctx: JavaParser.ExprLogicOrContext):
        # expression bop='||' expression
        self.visitBinaryExpression(ctx)
        # return self.visit(ctx.expression(0)) + " " + ctx.bop.text + " " + self.visit(ctx.expression(1))

    # TODO Ternary AST
    def visitExprTernary(self, ctx: JavaParser.ExprTernaryContext):
        # <assoc=right> expression bop='?' expression ':' expression
        ternaryNode = ASNode(ASNodeKind.TERNARY)
        ternaryNode.setLineOfCode(ctx.start.line)
        ternaryNode.setSharedId(ctx)
        self.ast.addVertex(ternaryNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, ternaryNode))

        predicateNode = ASNode(ASNodeKind.TERNARY_PREDICATE)
        predicateNode.setLineOfCode(ctx.start.line)
        predicateNode.setSharedId(ctx)
        self.ast.addVertex(predicateNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, predicateNode))
        self.parentStack.push(predicateNode)
        self.visit(ctx.expression(0))
        self.parentStack.pop()

        trueNode = ASNode(ASNodeKind.TERNARY_TRUE)
        trueNode.setLineOfCode(ctx.start.line)
        trueNode.setSharedId(ctx)
        self.ast.addVertex(trueNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, trueNode))
        self.parentStack.push(trueNode)
        self.visit(ctx.expression(1))
        self.parentStack.pop()

        falseNode = ASNode(ASNodeKind.TERNARY_FALSE)
        falseNode.setLineOfCode(ctx.start.line)
        falseNode.setSharedId(ctx)
        self.ast.addVertex(falseNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, falseNode))
        self.parentStack.push(falseNode)
        self.visit(ctx.expression(2))
        self.parentStack.pop()


    def visitExprAssign(self, ctx: JavaParser.ExprAssignContext):
        # <assoc=right> expression
        #       bop=('=' | '+=' | '-=' | '*=' | '/=' | '&=' | '|=' | '^=' | '>>=' | '>>>=' | '<<=' | '%=')
        #       expression
        assignNode = ASNode(ASNodeKind.ASSIGN)
        assignNode.setLineOfCode(ctx.start.line)
        assignNode.setSharedId(ctx)
        assignNode.setOptionalProperty("assignmentExpression", getOriginalCodeText(ctx.expression(1)))
        self.ast.addVertex(assignNode)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, assignNode))

        leftExpr = ctx.expression(0)
        leftNode = ASNode(ASNodeKind.ASSIGN_LEFT)
        leftNode.setLineOfCode(leftExpr.start.line)
        leftNode.setSharedId(leftExpr)
        self.ast.addVertex(leftNode)
        self.ast.addEdge(Edge(assignNode, None, leftNode))
        self.parentStack.push(leftNode)
        self.visit(leftExpr)
        self.parentStack.pop()

        rightExpr = ctx.expression(1)
        rightNode = ASNode(ASNodeKind.ASSIGN_RIGHT)
        rightNode.setLineOfCode(rightExpr.start.line)
        rightNode.setSharedId(rightExpr)
        self.ast.addVertex(rightNode)
        self.ast.addEdge(Edge(assignNode, None, rightNode))
        self.parentStack.push(rightNode)
        self.visit(rightExpr)
        self.parentStack.pop()

    def visitVariableInitializer(self, ctx: JavaParser.VariableInitializerContext):
        # variableInitializer
        #     : arrayInitializer
        #     | expression
        if ctx.expression() is not None:
            return self.visit(ctx.expression())
        else:
            return self.visit(ctx.arrayInitializer())


    def visitArrayInitializer(self, ctx: JavaParser.ArrayInitializerContext):
        # arrayInitializer
        #     : '{' (variableInitializer (',' variableInitializer)* (',')? )? '}'
        arrayInit = ASNode(ASNodeKind.ARRAY_INIT)
        arrayInit.setLineOfCode(ctx.start.line)
        arrayInit.setSharedId(ctx)
        self.ast.addVertex(arrayInit)
        self.ast.addEdge(Edge(self.parentStack.peek(), None, arrayInit))
        self.parentStack.push(arrayInit)
        if ctx.variableInitializer() is not None:
            # arrayInitializerStr = "{ "
            # for varInitCtx in ctx.variableInitializer():
            #     arrayInitializerStr += ", " + self.visit(varInitCtx)
            # return arrayInitializerStr
            for varInitCtx in ctx.variableInitializer():
                self.visit(varInitCtx)
        self.parentStack.pop()
        return "{ }"

    def visitExpressionList(self, ctx: JavaParser.ExpressionListContext):
        # expressionList
        #     : expression (',' expression)*
        for exprCtx in ctx.expression():
            self.visit(exprCtx)

    # *******************************************************************
    # ***                        Helper methods                       ***
    # *******************************************************************

    def resetLocalVars(self):
        self.vars.clear()
        self.varsCounter = 0
