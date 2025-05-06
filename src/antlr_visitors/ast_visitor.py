from antlr4 import ParserRuleContext

from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from graphs.ast.ast_node import ASNode, ASNodeKind
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from utils.datatypes import Stack
from utils.parsing import getOriginalCodeText, getIdByCtx, SyntheticNode

BinaryOperationContext = (
    JavaParser.ExprAddSubContext |
    JavaParser.ExprMulDivModContext |
    JavaParser.ExprBitShiftContext |
    JavaParser.ExprComparisonContext |
    JavaParser.ExprInstanceOfContext |
    JavaParser.ExprEqualityContext |
    JavaParser.ExprBitAndContext |
    JavaParser.ExprBitXorContext |
    JavaParser.ExprBitOrContext |
    JavaParser.ExprLogicAndContext |
    JavaParser.ExprLogicOrContext
)



class THEN(SyntheticNode):
    def __init__(self, true_clause_ctx):
        super().__init__(true_clause_ctx.start.start, true_clause_ctx.stop.stop)

class LOOP_BLOCK(SyntheticNode):
    def __init__(self, statement_ctx):
        super().__init__(statement_ctx.start.start, statement_ctx.stop.stop)

class ASTVisitor(JavaParserVisitor):
    def __init__(self, ast: AbstractSyntaxTreeNX, filename: str | None = None):
        self.ast = ast
        self.filename = filename
        self.parentStack = Stack(ASNode)

        self.root = self.ast.add_node(kind=ASNodeKind.ROOT, code="Filename")
        self.parentStack.push(self.root)
        self.typeModifier = ""
        self.memberModifier = ""
        self.vars = dict()
        self.varsCounter = 0

    # ************************************************************
    # ***                  DECLARATIONS                        ***
    # ************************************************************

    def visitPackageDeclaration(self, ctx: JavaParser.PackageDeclarationContext):
        # packageDeclaration: annotation* PACKAGE qualifiedName ';'
        # self.ast.set_property("package", ctx.qualifiedName().getText())
        package_node = self.add_node(
            kind=ASNodeKind.PACKAGE,
            code=ctx.qualifiedName().getText(),
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), package_node)

    def visitImportDeclaration(self, ctx: JavaParser.ImportDeclarationContext):
        # importDeclaration: IMPORT STATIC? qualifiedName ('.' '*')? ';'
        qualified_name = ctx.qualifiedName().getText()
        last = ctx.getChildCount() - 1

        if ctx.getText()[last - 1] == "*" and ctx.getText()[last - 2] == ".":
            qualified_name += ".*"

        import_node = self.add_node(
            kind=ASNodeKind.IMPORT,
            code=qualified_name,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), import_node)

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
        class_node = self.add_node(
            kind=ASNodeKind.CLASS,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), class_node)

        modifier_node = self.add_node(
            kind=ASNodeKind.MODIFIER,
            code=self.typeModifier,
            line=ctx.start.line
        )
        self.ast.add_edge(class_node, modifier_node)

        name_node = self.add_node(
            kind=ASNodeKind.NAME,
            code=ctx.IDENTIFIER().getText(),
            line=ctx.IDENTIFIER().symbol.line,
            shared_id=self.calculate_shared_id(ctx.IDENTIFIER())
        )
        self.ast.add_edge(class_node, name_node)

        if ctx.typeType() is not None:
            extends_node = self.add_node(
                kind=ASNodeKind.EXTENDS,
                code=ctx.typeType().getText(),
                line=ctx.typeType().start.line,
                shared_id=self.calculate_shared_id(ctx.typeType())
            )
            self.ast.add_edge(class_node, extends_node)

        if ctx.typeList() is not None:
            implements_node = self.add_node(
                kind=ASNodeKind.IMPLEMENTS,
                line=ctx.typeList().start.line,
                shared_id=self.calculate_shared_id(ctx.typeList())
            )
            self.ast.add_edge(class_node, implements_node)

            for typeCtx in ctx.typeList().typeType():
                interface_node = self.add_node(
                    kind=ASNodeKind.INTERFACE,
                    line=typeCtx.start.line,
                    code=typeCtx.getText(),
                    shared_id=self.calculate_shared_id(typeCtx)
                )
                self.ast.add_edge(implements_node, interface_node)

        self.parentStack.push(class_node)
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

        if (block_ctx := ctx.block()) is not None:
            static_block= self.add_node(
                kind=ASNodeKind.STATIC_BLOCK,
                line=block_ctx.start.line,
                shared_id=self.calculate_shared_id(block_ctx)
            )
            self.ast.add_edge(self.parentStack.peek(), static_block)
            self.parentStack.push(static_block)
            self.visitChildren(block_ctx)
            self.parentStack.pop()
        elif ctx.memberDeclaration() is not None:
            self.memberModifier = ""
            for modCtx in ctx.modifier():
                self.memberModifier += modCtx.getText() + " "
            self.memberModifier = self.memberModifier.rstrip()

            if (field_declaration_ctx := ctx.memberDeclaration().fieldDeclaration()) is not None:
                field_node = self.add_node(
                    kind=ASNodeKind.FIELD,
                    line=field_declaration_ctx.start.line,
                    shared_id=self.calculate_shared_id(field_declaration_ctx)
                )
                self.ast.add_edge(self.parentStack.peek(), field_node)
                self.parentStack.push(field_node)
                self.visit(field_declaration_ctx)
                self.parentStack.pop()
            elif (ctor_declaration_ctx := ctx.memberDeclaration().constructorDeclaration()) is not None:
                constructor_node = self.add_node(
                    kind=ASNodeKind.CONSTRUCTOR,
                    line=ctor_declaration_ctx.start.line,
                    shared_id=self.calculate_shared_id(ctor_declaration_ctx)
                )
                self.ast.add_edge(self.parentStack.peek(), constructor_node)
                self.parentStack.push(constructor_node)
                self.visit(ctor_declaration_ctx)
                self.parentStack.pop()
            elif (method_declaration_ctx := ctx.memberDeclaration().methodDeclaration()) is not None:
                method_node = self.add_node(
                    kind=ASNodeKind.METHOD,
                    line=method_declaration_ctx.start.line,
                    shared_id=self.calculate_shared_id(method_declaration_ctx)
                )
                self.ast.add_edge(self.parentStack.peek(), method_node)
                self.parentStack.push(method_node)
                self.visit(method_declaration_ctx)
                self.parentStack.pop()
            else:
                self.visitChildren(ctx.memberDeclaration())

    def visitConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
        # constructorDeclaration
        #     : IDENTIFIER formalParameters (THROWS qualifiedNameList)? constructorBody=block

        modifier_node = self.add_node(
            kind=ASNodeKind.MODIFIER,
            line=ctx.start.line,
            code=self.memberModifier  # TODO: выяснить почему
        )
        self.ast.add_edge(self.parentStack.peek(), modifier_node)

        if ctx.formalParameters().formalParameterList() is not None:
            params_node = self.add_node(
                kind=ASNodeKind.PARAMS,
                line=ctx.formalParameters().formalParameterList().start.line,
                shared_id=self.calculate_shared_id(ctx.formalParameters().formalParameterList())
            )
            self.ast.add_edge(self.parentStack.peek(), params_node)
            self.parentStack.push(params_node)

            for paramCtx in ctx.formalParameters().formalParameterList().formalParameter():
                var_node = self.add_node(
                    kind=ASNodeKind.VARIABLE,
                    line=paramCtx.start.line,
                    shared_id=self.calculate_shared_id(paramCtx)
                )
                self.ast.add_edge(self.parentStack.peek(), var_node)

                type_node = self.add_node(
                    kind=ASNodeKind.TYPE,
                    line=paramCtx.typeType().start.line,
                    code=paramCtx.typeType().getText(),
                    shared_id=self.calculate_shared_id(paramCtx.typeType())
                )
                self.ast.add_edge(var_node, type_node)

                name_node = self.add_node(
                    kind=ASNodeKind.NAME,
                    line=paramCtx.variableDeclaratorId().start.line,
                    code=paramCtx.variableDeclaratorId().getText(),
                    shared_id=self.calculate_shared_id(paramCtx.variableDeclaratorId())
                )
                self.ast.add_edge(var_node, name_node)

            if ctx.formalParameters().formalParameterList().lastFormalParameter() is not None:
                lfp_ctx = ctx.formalParameters().formalParameterList().lastFormalParameter()
                var_node = self.add_node(
                    kind=ASNodeKind.VARIABLE,
                    line=lfp_ctx.start.line,
                    shared_id=self.calculate_shared_id(lfp_ctx)
                )
                self.ast.add_edge(self.parentStack.peek(), var_node)

                # TODO: переименовать type_node
                type_node = self.add_node(
                    kind=ASNodeKind.TYPE,
                    line=lfp_ctx.typeType().start.line,
                    code=lfp_ctx.typeType().getText(),
                    shared_id=self.calculate_shared_id(lfp_ctx.typeType())
                )
                self.ast.add_edge(var_node, type_node)

                # TODO: переименовать name_node
                name_node = self.add_node(
                    kind=ASNodeKind.NAME,
                    line=lfp_ctx.variableDeclaratorId().start.line,
                    code=lfp_ctx.variableDeclaratorId().getText(),
                    shared_id=self.calculate_shared_id(lfp_ctx.variableDeclaratorId())
                )
                self.ast.add_edge(var_node, name_node)

            self.parentStack.pop()

        body_block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=ctx.constructorBody.start.line,
            shared_id=self.calculate_shared_id(ctx.constructorBody)
        )
        self.ast.add_edge(self.parentStack.peek(), body_block)
        self.parentStack.push(body_block)
        self.visitChildren(ctx.constructorBody)
        self.parentStack.pop()
        self.resetLocalVars()

    def visitFieldDeclaration(self, ctx: JavaParser.FieldDeclarationContext):
        # fieldDeclaration: typeType variableDeclarators ';'
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?

        for varCtx in ctx.variableDeclarators().variableDeclarator():
            modifier_node = self.add_node(
                kind=ASNodeKind.MODIFIER,
                line=ctx.start.line,
                code=self.memberModifier
            )
            self.ast.add_edge(self.parentStack.peek(), modifier_node)

            type_node = self.add_node(
                kind=ASNodeKind.TYPE,
                line=ctx.typeType().start.line,
                code=ctx.typeType().getText(),
                shared_id=self.calculate_shared_id(ctx.typeType())
            )
            self.ast.add_edge(self.parentStack.peek(), type_node)

            name_node = self.add_node(
                kind=ASNodeKind.NAME,
                line=varCtx.variableDeclaratorId().start.line,
                code=varCtx.variableDeclaratorId().getText(),
                shared_id=self.calculate_shared_id(varCtx.variableDeclaratorId())
            )
            self.ast.add_edge(self.parentStack.peek(), name_node)

            if varCtx.variableInitializer() is not None:
                init_node = self.add_node(
                    kind=ASNodeKind.INIT_VALUE,
                    line=varCtx.variableInitializer().start.line,
                    code="=",  # TODO: перепроверить, точно ли здесь просто "="?
                    shared_id=self.calculate_shared_id(varCtx.variableInitializer())
                )
                self.ast.add_edge(self.parentStack.peek(), init_node)
                self.parentStack.push(init_node)
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

        modifier_node = self.add_node(
            kind=ASNodeKind.MODIFIER,
            line=ctx.start.line,
            code=self.memberModifier
        )
        self.ast.add_edge(self.parentStack.peek(), modifier_node)

        ret_node = self.add_node(
            kind=ASNodeKind.RET_VAL_TYPE,
            line=ctx.start.line,
            code=ctx.typeTypeOrVoid().getText(),
            shared_id=self.calculate_shared_id(ctx.typeTypeOrVoid())
        )
        self.ast.add_edge(self.parentStack.peek(), ret_node)

        name_node = self.add_node(
            kind=ASNodeKind.NAME,
            line=ctx.start.line,
            code=ctx.IDENTIFIER().getText()
        )
        self.ast.add_edge(self.parentStack.peek(), name_node)

        if ctx.formalParameters().formalParameterList() is not None:
            params_node = self.add_node(
                kind=ASNodeKind.PARAMS,
                line=ctx.formalParameters().formalParameterList().start.line,
                shared_id=self.calculate_shared_id(ctx.formalParameters().formalParameterList())
            )
            self.ast.add_edge(self.parentStack.peek(), params_node)
            self.parentStack.push(params_node)

            for paramCtx in ctx.formalParameters().formalParameterList().formalParameter():
                var_node = self.add_node(
                    kind=ASNodeKind.VARIABLE,
                    line=paramCtx.start.line,
                    shared_id=self.calculate_shared_id(paramCtx)
                )
                self.ast.add_edge(self.parentStack.peek(), var_node)

                type_node = self.add_node(
                    kind=ASNodeKind.TYPE,
                    line=paramCtx.typeType().start.line,
                    code=paramCtx.typeType().getText(),
                    shared_id=self.calculate_shared_id(paramCtx.typeType())
                )
                self.ast.add_edge(var_node, type_node)

                # TODO: change name
                name_node = self.add_node(
                    kind=ASNodeKind.NAME,
                    line=paramCtx.variableDeclaratorId().start.line,
                    code=paramCtx.variableDeclaratorId().getText(),
                    shared_id=self.calculate_shared_id(paramCtx.variableDeclaratorId())
                )
                self.ast.add_edge(var_node, name_node)

            if ctx.formalParameters().formalParameterList().lastFormalParameter() is not None:
                lfp_ctx = ctx.formalParameters().formalParameterList().lastFormalParameter()
                # TODO: change name
                var_node = self.add_node(
                    kind=ASNodeKind.VARIABLE,
                    line=lfp_ctx.start.line,
                    shared_id=self.calculate_shared_id(lfp_ctx)
                )
                self.ast.add_edge(self.parentStack.peek(), var_node)

                # TODO: change name
                type_node = self.add_node(
                    kind=ASNodeKind.TYPE,
                    line=lfp_ctx.typeType().start.line,
                    code=lfp_ctx.typeType().getText(),
                    shared_id=self.calculate_shared_id(lfp_ctx.typeType())
                )
                self.ast.add_edge(var_node, type_node)

                # TODO: change name
                name_node = self.add_node(
                    kind=ASNodeKind.NAME,
                    line=lfp_ctx.variableDeclaratorId().start.line,
                    code=lfp_ctx.variableDeclaratorId().getText(),
                    shared_id=self.calculate_shared_id(lfp_ctx.variableDeclaratorId())
                )
                self.ast.add_edge(var_node, name_node)

            self.parentStack.pop()

        if ctx.methodBody().block() is not None:
            body_block = self.add_node(
                kind=ASNodeKind.BLOCK,
                line=ctx.methodBody().block().start.line,
                shared_id=self.calculate_shared_id(ctx.methodBody().block())
            )
            self.ast.add_edge(self.parentStack.peek(), body_block)
            self.parentStack.push(body_block)
            self.visitChildren(ctx.methodBody().block())
            self.parentStack.pop()
            self.resetLocalVars()

    def visitLocalVariableDeclaration(self, ctx: JavaParser.LocalVariableDeclarationContext):
        # localVariableDeclaration: variableModifier* typeType variableDeclarators
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?

        for varCtx in ctx.variableDeclarators().variableDeclarator():
            var_node = self.add_node(
                kind=ASNodeKind.VARIABLE,
                line=varCtx.start.line,
                shared_id=self.calculate_shared_id(varCtx)
            )
            self.ast.add_edge(self.parentStack.peek(), var_node)

            type_node = self.add_node(
                kind=ASNodeKind.TYPE,
                line=ctx.typeType().start.line,
                code=ctx.typeType().getText(),
                shared_id=self.calculate_shared_id(ctx.typeType())
            )
            self.ast.add_edge(var_node, type_node)

            name_node = self.add_node(
                kind=ASNodeKind.NAME,
                line=varCtx.variableDeclaratorId().start.line,
                code=varCtx.variableDeclaratorId().getText(),
                shared_id=self.calculate_shared_id(varCtx.variableDeclaratorId())
            )
            self.ast.add_edge(var_node, name_node)

            if (variable_initializer_ctx := varCtx.variableInitializer()) is not None:
                init_node = self.add_node(
                    kind=ASNodeKind.INIT_VALUE,
                    line=variable_initializer_ctx.start.line,
                    code="=",
                    shared_id=self.calculate_shared_id(variable_initializer_ctx)
                )
                self.ast.add_edge(var_node, init_node)
                self.parentStack.push(init_node)
                self.visit(variable_initializer_ctx)
                self.parentStack.pop()

    # *******************************************************************
    # ***                     STATEMENTS                              ***
    # *******************************************************************

    # TODO: разобравться зачем normalized
    def visitStatement(self, ctx: ParserRuleContext, normalized: str | None):
        stmt_node = self.add_node(
            kind=ASNodeKind.STATEMENT,
            line=ctx.start.line,
            code=getOriginalCodeText(ctx),
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), stmt_node)

    def visitStmtExpr(self, ctx: JavaParser.StmtExprContext):
        # statement: statementExpression=expression ';'
        stmt_node = self.add_node(
            kind=ASNodeKind.STATEMENT,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), stmt_node)
        self.parentStack.push(stmt_node)
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
            ret_node = self.add_node(
                kind=ASNodeKind.RETURN,
                line=ctx.start.line,
                shared_id=self.calculate_shared_id(ctx)
            )
            self.ast.add_edge(self.parentStack.peek(), ret_node)
            self.parentStack.push(ret_node)
            self.visit(ctx.expression())
            self.parentStack.pop()

    def visitStmtThrow(self, ctx: JavaParser.StmtThrowContext):
        # statement: THROW expression ';'
        self.visitStatement(ctx, "throw " + self.visit(ctx.expression()))

    def visitStmtSynchronized(self, ctx: JavaParser.StmtSynchronizedContext):
        # statement: SYNCHRONIZED parExpression block
        synch_node = self.add_node(
            kind=ASNodeKind.SYNC,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), synch_node)

        self.parentStack.push(synch_node)
        self.visitStatement(ctx.parExpression().expression(), self.visit(ctx.parExpression().expression()))
        self.parentStack.pop()

        block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=ctx.block().start.line,
            shared_id=self.calculate_shared_id(ctx.block())
        )
        self.ast.add_edge(synch_node, block)
        self.parentStack.push(block)
        self.visit(ctx.block())
        self.parentStack.pop()

    def visitStmtLabel(self, ctx: JavaParser.StmtLabelContext):
        # statement: identifierLabel=IDENTIFIER ':' statement
        label_node = self.add_node(
            kind=ASNodeKind.LABELED,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), label_node)

        name_node = self.add_node(
            kind=ASNodeKind.NAME,
            line=ctx.start.line,
            code=ctx.IDENTIFIER().getText(),
            shared_id=self.calculate_shared_id(ctx.IDENTIFIER())
        )
        self.ast.add_edge(label_node, name_node)

        self.parentStack.push(label_node)
        self.visit(ctx.statement())
        self.parentStack.pop()

    def visitStmtIf(self, ctx: JavaParser.StmtIfContext):
        # statement: IF parExpression trueClause=statement (ELSE falseClause=statement)?
        if_node = self.add_node(
            kind=ASNodeKind.IF,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), if_node)

        condition_node = self.add_node(
            kind=ASNodeKind.CONDITION,
            line=ctx.parExpression().start.line,
            shared_id=self.calculate_shared_id(ctx.parExpression())
        )
        self.ast.add_edge(if_node, condition_node)
        self.parentStack.push(condition_node)
        self.visit(ctx.parExpression())
        self.parentStack.pop()

        then_node = self.add_node(
            kind=ASNodeKind.THEN,
            line=ctx.trueClause.start.line,
            shared_id=self.calculate_shared_id(THEN(ctx.trueClause))
        )
        self.ast.add_edge(if_node, then_node)
        self.parentStack.push(then_node)
        self.visit(ctx.trueClause)
        self.parentStack.pop()

        if ctx.falseClause is not None:
            else_node = self.add_node(
                kind=ASNodeKind.ELSE,
                line=ctx.falseClause.start.line,
                shared_id=self.calculate_shared_id(ctx.ELSE())
            )
            self.ast.add_edge(if_node, else_node)
            self.parentStack.push(else_node)
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
            for_node = self.add_node(
                kind=ASNodeKind.FOR_EACH,
                line=ctx.start.line,
                shared_id=self.calculate_shared_id(ctx)
            )
            self.ast.add_edge(self.parentStack.peek(), for_node)

            var_type = self.add_node(
                kind=ASNodeKind.TYPE,
                line=ctx.forControl().enhancedForControl().typeType().start.line,
                code=ctx.forControl().enhancedForControl().typeType().getText(),
                shared_id=self.calculate_shared_id(ctx.forControl().enhancedForControl().typeType())
            )
            self.ast.add_edge(for_node, var_type)

            var_id = self.add_node(
                kind=ASNodeKind.NAME,
                line=ctx.forControl().enhancedForControl().variableDeclaratorId().start.line,
                code=ctx.forControl().enhancedForControl().variableDeclaratorId().getText(),
                shared_id=self.calculate_shared_id(ctx.forControl().enhancedForControl().variableDeclaratorId())
            )
            self.ast.add_edge(for_node, var_id)

            in_node = self.add_node(
                kind=ASNodeKind.FOR_IN,
                line=ctx.forControl().enhancedForControl().expression().start.line,
                # code=getOriginalCodeText(ctx.forControl().enhancedForControl().expression()),
                # shared_id=self.calculate_shared_id(ctx.forControl().enhancedForControl().expression())
            )
            self.ast.add_edge(for_node, in_node)
            self.parentStack.push(in_node)
            self.visit(ctx.forControl().enhancedForControl().expression())
            self.parentStack.pop()
        else:
            for_node = self.add_node(
                kind=ASNodeKind.FOR,
                line=ctx.start.line,
                shared_id=self.calculate_shared_id(ctx)
            )
            self.ast.add_edge(self.parentStack.peek(), for_node)

            if (for_init_ctx := ctx.forControl().forInit()) is not None:
                for_init = self.add_node(
                    kind=ASNodeKind.FOR_INIT,
                    line=for_init_ctx.start.line,
                    shared_id=self.calculate_shared_id(for_init_ctx)
                )
                self.ast.add_edge(for_node, for_init)

                if for_init_ctx.localVariableDeclaration() is not None:
                    self.parentStack.push(for_init)
                    self.visit(for_init_ctx.localVariableDeclaration())
                    self.parentStack.pop()
                else:
                    expression_ctx = for_init_ctx.expressionList().expression(0)
                    expr = self.add_node(
                        kind=ASNodeKind.STATEMENT,
                        line=expression_ctx.start.line,
                        code=getOriginalCodeText(expression_ctx),
                        shared_id=self.calculate_shared_id(expression_ctx)
                    )
                    self.ast.add_edge(for_init, expr)

                    # TODO: refactor
                    for expr_ctx in for_init_ctx.expressionList().expression()[1:]:
                        expr = self.add_node(
                            kind=ASNodeKind.STATEMENT,
                            line=expr_ctx.start.line,
                            code=getOriginalCodeText(expr_ctx),
                            shared_id=self.calculate_shared_id(expr_ctx)
                        )
                        self.ast.add_edge(for_init, expr)

            if (for_expr_ctx := ctx.forControl().expression()) is not None:
                for_expr = self.add_node(
                    kind=ASNodeKind.CONDITION,
                    line=for_expr_ctx.start.line,
                    shared_id=self.calculate_shared_id(for_expr_ctx)
                )
                self.ast.add_edge(for_node, for_expr)
                self.parentStack.push(for_expr)
                self.visit(for_expr_ctx)
                self.parentStack.pop()

            if (for_update_ctx := ctx.forControl().forUpdate) is not None:
                for_update = self.add_node(
                    kind=ASNodeKind.FOR_UPDATE,
                    line=for_update_ctx.start.line,
                    shared_id=self.calculate_shared_id(for_update_ctx)
                )
                self.ast.add_edge(for_node, for_update)

                for_update_expression_ctx = for_update_ctx.expression(0)
                expr = self.add_node(
                    kind=ASNodeKind.STATEMENT,
                    line=for_update_expression_ctx.start.line,  # TODO: здесь code не надо задавать как ниже?
                    shared_id=self.calculate_shared_id(for_update_expression_ctx)
                )
                self.ast.add_edge(for_update, expr)
                self.parentStack.push(expr)
                self.visit(for_update_expression_ctx)
                self.parentStack.pop()

                # TODO: refactor
                for expr_ctx in ctx.forControl().forUpdate.expression()[1:]:
                    expr = self.add_node(
                        kind=ASNodeKind.STATEMENT,
                        line=expr_ctx.start.line,
                        code=getOriginalCodeText(expr_ctx),
                        shared_id=self.calculate_shared_id(expr_ctx)
                    )
                    self.ast.add_edge(for_update, expr)
                    self.parentStack.push(expr)
                    self.visit(expr_ctx)
                    self.parentStack.pop()

        statement_ctx = ctx.statement()
        block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=statement_ctx.start.line,
            shared_id=self.calculate_shared_id(LOOP_BLOCK(statement_ctx))
        )
        self.ast.add_edge(for_node, block)
        self.parentStack.push(block)
        self.visit(statement_ctx)
        self.parentStack.pop()

    def visitStmtWhile(self, ctx: JavaParser.StmtWhileContext):
        # statement: WHILE parExpression statement

        while_node = self.add_node(
            kind=ASNodeKind.WHILE,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), while_node)

        condition_ctx = ctx.parExpression().expression()
        condition_node = self.add_node(
            kind=ASNodeKind.CONDITION,
            line=condition_ctx.start.line,
            shared_id=self.calculate_shared_id(condition_ctx)
        )
        self.ast.add_edge(while_node, condition_node)
        self.parentStack.push(condition_node)
        self.visit(condition_ctx)
        self.parentStack.pop()

        statement_ctx = ctx.statement()
        block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=statement_ctx.start.line,
            shared_id=self.calculate_shared_id(LOOP_BLOCK(statement_ctx))
        )
        self.ast.add_edge(while_node, block)
        self.parentStack.push(block)
        self.visit(statement_ctx)
        self.parentStack.pop()

    def visitStmtDoWhile(self, ctx: JavaParser.StmtDoWhileContext):
        # statement: DO statement WHILE parExpression ';'

        do_while_node = self.add_node(
            kind=ASNodeKind.DO_WHILE,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), do_while_node)

        condition_ctx = ctx.parExpression().expression()
        condition_node = self.add_node(
            kind=ASNodeKind.CONDITION,
            line=condition_ctx.start.line,
            code=getOriginalCodeText(condition_ctx),
            shared_id=self.calculate_shared_id(condition_ctx)
        )
        self.ast.add_edge(do_while_node, condition_node)

        statement_ctx = ctx.statement()
        block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=statement_ctx.start.line,
            shared_id=self.calculate_shared_id(LOOP_BLOCK(statement_ctx))
        )
        self.ast.add_edge(do_while_node, block)
        self.parentStack.push(block)
        self.visit(statement_ctx)
        self.parentStack.pop()

    def visitStmtTry(self, ctx: JavaParser.StmtTryContext):
        # statement: TRY block (catchClause+ finallyBlock? | finallyBlock)

        try_node = self.add_node(
            kind=ASNodeKind.TRY,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), try_node)

        block_ctx = ctx.block()
        try_block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=block_ctx.start.line,
            shared_id=self.calculate_shared_id(block_ctx)
        )
        self.ast.add_edge(try_node, try_block)
        self.parentStack.push(try_block)
        self.visit(block_ctx)
        self.parentStack.pop()

        if (catch_clause_ctx := ctx.catchClause()) is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block

            for catchCtx in catch_clause_ctx:
                catch_node = self.add_node(
                    kind=ASNodeKind.CATCH,
                    line=catchCtx.start.line,
                    shared_id=self.calculate_shared_id(catchCtx)
                )
                self.ast.add_edge(try_node, catch_node)

                catch_type_ctx = catchCtx.catchType()
                catch_type = self.add_node(
                    kind=ASNodeKind.TYPE,
                    line=catch_type_ctx.start.line,
                    code=catch_type_ctx.getText(),
                    shared_id=self.calculate_shared_id(catch_type_ctx)
                )
                self.ast.add_edge(catch_node, catch_type)

                catch_name = self.add_node(
                    kind=ASNodeKind.NAME,
                    line=catchCtx.IDENTIFIER().symbol.line,
                    code=catchCtx.IDENTIFIER().getText(), # TODO: может можно как-то извлекать номер строки?
                    shared_id=self.calculate_shared_id(catchCtx.IDENTIFIER())
                )
                self.ast.add_edge(catch_node, catch_name)

                catch_block_ctx = catchCtx.block()
                catch_block = self.add_node(
                    kind=ASNodeKind.BLOCK,
                    line=catch_block_ctx.start.line,
                    shared_id=self.calculate_shared_id(catch_block_ctx)
                )
                self.ast.add_edge(catch_node, catch_block)
                self.parentStack.push(catch_block)
                self.visit(catch_block_ctx)
                self.parentStack.pop()

        if (finally_block_ctx := ctx.finallyBlock()) is not None:
            # finallyBlock: FINALLY block

            finally_node = self.add_node(
                kind=ASNodeKind.FINALLY,
                line=finally_block_ctx.start.line,
                shared_id=self.calculate_shared_id(finally_block_ctx)
            )
            self.ast.add_edge(try_node, finally_node)
            self.parentStack.push(finally_node)
            self.visit(finally_block_ctx.block())
            self.parentStack.pop()

    def visitStmtTryResource(self, ctx: JavaParser.StmtTryResourceContext):
        # statement: TRY resourceSpecification block catchClause* finallyBlock?
        # resourceSpecification: '(' resources ';'? ')'
        # resources: resource (';' resource)*
        # resource: variableModifier* classOrInterfaceType variableDeclaratorId '=' expression

        try_node = self.add_node(
            kind=ASNodeKind.TRY,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), try_node)

        resource_specification_ctx = ctx.resourceSpecification()
        res_node = self.add_node(
            kind=ASNodeKind.RESOURCES,
            line=resource_specification_ctx.start.line,
            shared_id=self.calculate_shared_id(resource_specification_ctx)
        )
        self.ast.add_edge(try_node, res_node)

        for resCtx in ctx.resourceSpecification().resources().resource():
            var_node = self.add_node(
                kind=ASNodeKind.VARIABLE,
                line=resCtx.start.line,
                shared_id=self.calculate_shared_id(resCtx)
            )
            self.ast.add_edge(res_node, var_node)

            class_or_interface_type_ctx = resCtx.classOrInterfaceType()
            res_type = self.add_node(
                kind=ASNodeKind.TYPE,
                line=class_or_interface_type_ctx.start.line,
                code=class_or_interface_type_ctx.getText(),
                shared_id=self.calculate_shared_id(class_or_interface_type_ctx)
            )
            self.ast.add_edge(res_node, res_type)

            variable_declarator_id_ctx = resCtx.variableDeclaratorId()
            res_name = self.add_node(
                kind=ASNodeKind.NAME,
                line=variable_declarator_id_ctx.start.line,
                code=variable_declarator_id_ctx.getText(),
                shared_id=self.calculate_shared_id(variable_declarator_id_ctx)
            )
            self.ast.add_edge(res_node, res_name)

            res_init = self.add_node(
                kind=ASNodeKind.INIT_VALUE,
                line=resCtx.expression().start.line,
                shared_id=self.calculate_shared_id(resCtx)  # TODO: здесь не должно быть resCtx.expression()?
            )
            self.ast.add_edge(res_node, res_init)
            self.parentStack.push(res_init)
            self.visit(resCtx.expression())
            self.parentStack.pop()

        block_ctx = ctx.block()
        try_block = self.add_node(
            kind=ASNodeKind.BLOCK,
            line=block_ctx.start.line,
            shared_id=self.calculate_shared_id(block_ctx)
        )
        self.ast.add_edge(try_node, try_block)
        self.parentStack.push(try_block)
        self.visit(block_ctx)
        self.parentStack.pop()

        if (catch_clause_ctx := ctx.catchClause()) is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block

            for catchCtx in catch_clause_ctx:
                catch_node = self.add_node(
                    kind=ASNodeKind.CATCH,
                    line=catchCtx.start.line,
                    shared_id=self.calculate_shared_id(catchCtx)
                )
                self.ast.add_edge(try_node, catch_node)

                catch_type_ctx = catchCtx.catchType()
                catch_type = self.add_node(
                    kind=ASNodeKind.TYPE,
                    line=catch_type_ctx.start.line,
                    code=catch_type_ctx.getText(),
                    shared_id=self.calculate_shared_id(catch_type_ctx)
                )
                self.ast.add_edge(catch_node, catch_type)

                catch_id_ctx = catchCtx.IDENTIFIER()
                catch_name = self.add_node(
                    kind=ASNodeKind.NAME,
                    line=catch_id_ctx.symbol.line,
                    code=catch_id_ctx.getText(),
                    shared_id=self.calculate_shared_id(catch_id_ctx)
                )
                self.ast.add_edge(catch_node, catch_name)

                catch_block_ctx = catchCtx.block()
                catch_block = self.add_node(
                    kind=ASNodeKind.BLOCK,
                    line=catch_block_ctx.start.line,
                    shared_id=self.calculate_shared_id(catch_block_ctx)
                )
                self.ast.add_edge(catch_node, catch_block)
                self.parentStack.push(catch_block)
                self.visit(catch_block_ctx)
                self.parentStack.pop()

        if (finally_block_ctx := ctx.finallyBlock()) is not None:
            # finallyBlock: FINALLY block

            finally_node = self.add_node(
                kind=ASNodeKind.FINALLY,
                line=finally_block_ctx.start.line,
                shared_id=self.calculate_shared_id(finally_block_ctx)
            )
            self.ast.add_edge(try_node, finally_node)
            self.parentStack.push(finally_node)
            self.visit(finally_block_ctx.block())
            self.parentStack.pop()

    def visitStmtSwitch(self, ctx: JavaParser.StmtSwitchContext):
        # statement: SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'
        # switchBlockStatementGroup: switchLabel+ blockStatement+
        # switchLabel
        #     : CASE (constantExpression=expression | enumConstantName=IDENTIFIER) ':'
        #     | DEFAULT ':'

        switch_node = self.add_node(
            kind=ASNodeKind.SWITCH,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), switch_node)

        var_name_ctx = ctx.parExpression().expression()
        var_name = self.add_node(
            kind=ASNodeKind.NAME,
            line=var_name_ctx.start.line,
            code=var_name_ctx.getText(),
            shared_id=self.calculate_shared_id(var_name_ctx)
        )
        self.ast.add_edge(switch_node, var_name)

        if ctx.switchBlockStatementGroup() is not None:
            for groupCtx in ctx.switchBlockStatementGroup():
                block_node = self.add_node(
                    kind=ASNodeKind.BLOCK,
                    line=groupCtx.blockStatement(0).start.line,
                    shared_id=self.calculate_shared_id(groupCtx.blockStatement(0))
                )
                self.parentStack.push(block_node)
                for lblCtx in ctx.switchBlockStatementGroup().switchLabel():
                    self.visit(lblCtx)
                for stmtCtx in ctx.switchBlockStatementGroup().blockStatement():
                    self.visit(stmtCtx)
                self.parentStack.pop()

        if ctx.switchLabel() is not None:
            self.parentStack.push(switch_node)
            for lblCtx in ctx.switchLabel():
                self.visit(lblCtx)
            self.parentStack.pop()

    def visitSwitchLabel(self, ctx: JavaParser.SwitchLabelContext):
        # switchLabel
        #     : CASE (constantExpression=expression | enumConstantName=IDENTIFIER) ':'
        #     | DEFAULT ':'
        if (constant_expression_ctx := ctx.constantExpression()) is not None:
            kind = ASNodeKind.CASE
            line = constant_expression_ctx.start.line
        elif (enum_constant_name_ctx := ctx.enumConstantName()) is not None:
            kind = ASNodeKind.CASE
            line = enum_constant_name_ctx.start.line
        else:
            kind = ASNodeKind.DEFAULT
            line = ctx.start.line

        case_node = self.add_node(
            kind=kind,
            line=line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), case_node)

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
        primary_ctx = ctx.primary()

        if primary_ctx.expression() is not None:
            # return "(" + self.visit(primary.expression()) + ")"
            self.visit(primary_ctx.expression())

        if primary_ctx.IDENTIFIER() is not None:
            id_node = self.add_node(
                kind=ASNodeKind.NAME,
                line=primary_ctx.start.line,
                code=primary_ctx.IDENTIFIER().getText(),
                shared_id=self.calculate_shared_id(primary_ctx.IDENTIFIER())
            )
            self.ast.add_edge(self.parentStack.peek(), id_node)

        if primary_ctx.THIS() is not None:
            this_node = self.add_node(
                kind=ASNodeKind.NAME,
                line=primary_ctx.start.line,
                code="this",
                shared_id=self.calculate_shared_id(primary_ctx.THIS())
            )
            self.ast.add_edge(self.parentStack.peek(), this_node)

        if primary_ctx.nonWildcardTypeArguments() is not None:
            if primary_ctx.arguments() is not None:
                return getOriginalCodeText(primary_ctx.nonWildcardTypeArguments()) \
                       + "this" + self.visit(primary_ctx.arguments())
            else:
                if primary_ctx.explicitGenericInvocationSuffix().IDENTIFIER() is not None:
                    suffix = primary_ctx.explicitGenericInvocationSuffix().IDENTIFIER().getText() + \
                             self.visit(primary_ctx.explicitGenericInvocationSuffix().arguments())
                else:
                    suffix = "super" + self.visit(primary_ctx.explicitGenericInvocationSuffix().superSuffix())
                return getOriginalCodeText(primary_ctx.nonWildcardTypeArguments()) + suffix

        if primary_ctx.literal() is not None:
            literal_node = self.add_node(
                kind=ASNodeKind.LITERAL,
                line=primary_ctx.literal().start.line,
                code=primary_ctx.literal().getText(),
                shared_id=self.calculate_shared_id(primary_ctx.literal())
            )
            self.ast.add_edge(self.parentStack.peek(), literal_node)
            return None

        # TODO: разобраться: мы реально где-то используем то, что здесь возвращается?
        return getOriginalCodeText(primary_ctx)

    def visitExprDot(self, ctx: JavaParser.ExprDotContext):
        # expression: expression bop='.'
        #       ( IDENTIFIER
        #       | methodCall
        #       | THIS
        #       | NEW nonWildcardTypeArguments? innerCreator
        #       | SUPER superSuffix
        #       | explicitGenericInvocation
        #       )                 # ExprDot

        dot_node = self.add_node(
            kind=ASNodeKind.DOT,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx.bop)
        )
        self.ast.add_edge(self.parentStack.peek(), dot_node)
        self.parentStack.push(dot_node)
        self.visit(ctx.expression())
        self.parentStack.pop()

        if ctx.IDENTIFIER() is not None:
            id_node = self.add_node(
                kind=ASNodeKind.NAME,
                line=ctx.start.line,
                code=ctx.IDENTIFIER().getText(),
                shared_id=self.calculate_shared_id(ctx.IDENTIFIER())
            )
            self.ast.add_edge(dot_node, id_node)
            # TODO: здесь и ниже не нужны return-ы?

        if ctx.THIS() is not None:
            # return self.visit(ctx.expression()) + ".this"

            this_node = self.add_node(
                kind=ASNodeKind.NAME,
                line=ctx.start.line,
                code="this",
                shared_id=self.calculate_shared_id(ctx.THIS())
            )
            self.ast.add_edge(dot_node, this_node)

        if ctx.NEW() is not None:
            return self.visit(ctx.expression()) + ".new " + getOriginalCodeText(ctx.nonWildcardTypeArguments()) \
                   + ctx.innerCreator().IDENTIFIER().getText() \
                   + getOriginalCodeText(ctx.innerCreator().nonWildcardTypeArgumentsOrDiamond()) \
                   + self.visit(ctx.innerCreator().classCreatorRest().arguments()) \
                   + self.visit(ctx.innerCreator().classCreatorRest().classBody())

        if ctx.SUPER() is not None:
            return self.visit(ctx.expression()) + ".super" + self.visit(ctx.superSuffix())

        if ctx.methodCall() is not None:
            self.parentStack.push(dot_node)
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

        super_suffix = ""

        if ctx.IDENTIFIER() is not None:
            super_suffix = "." + ctx.IDENTIFIER().getText()

        if ctx.arguments() is not None:
            super_suffix += self.visit(ctx.arguments())

        return super_suffix

    def visitArguments(self, ctx: JavaParser.ArgumentsContext):
        # arguments
        #     : '(' expressionList? ')'

        args_node = self.add_node(
            kind=ASNodeKind.ARGS,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), args_node)
        # if ctx.expressionList() is None:
        #     return "()"
        # return "(" + self.visit(ctx.expressionList()) + ")"
        if ctx.expressionList() is not None:
            self.parentStack.push(args_node)
            self.visit(ctx.expressionList())
            self.parentStack.pop()

    def visitExprArray(self, ctx: JavaParser.ExprArrayContext):
        # expression '[' expression ']'                    # ExprArray

        node = self.add_node(
            kind=ASNodeKind.ARRAY,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), node)
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
    #     self.add_node(nameNode)
    #     self.ast.add_edge(self.parentStack.peek(), None, nameNode))
    #
    #     if methodCall.expressionList():
    #         paramsNode = ASNode(ASNodeKind.PARAMS)
    #         paramsNode.setLineOfCode(methodCall.expressionList().start.line)
    #         self.add_node(paramsNode)
    #         self.ast.add_edge(self.parentStack.peek(), None, paramsNode))
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
            first_part = ctx.IDENTIFIER().getText()
        elif ctx.THIS() is not None:
            first_part = "this"
        else:
            first_part = "super"

        call_node = self.add_node(
            kind=ASNodeKind.CALL,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx),
            optional_properties=dict(name=first_part)
        )
        self.ast.add_edge(self.parentStack.peek(), call_node)

        name_node = self.add_node(
            kind=ASNodeKind.NAME,
            line=ctx.start.line,
            code=first_part,
            shared_id=self.calculate_shared_id(ctx.getChild(0))
        )
        self.ast.add_edge(call_node, name_node)

        if ctx.expressionList():
            # Bad code. It is needed for taint-flow analysis
            args = []
            for exprCtx in ctx.expressionList().expression():
                args.append(getOriginalCodeText(exprCtx))
            call_node.set_optional_property("args", args)

            params_node = self.add_node(
                kind=ASNodeKind.PARAMS,
                line=ctx.expressionList().start.line,
                shared_id=self.calculate_shared_id(ctx.expressionList())
            )
            self.ast.add_edge(call_node, params_node)
            self.parentStack.push(params_node)
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

        cast_node = self.add_node(
            kind=ASNodeKind.CAST,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), cast_node)

        type_type_ctx = ctx.typeType()
        type_node = self.add_node(
            kind=ASNodeKind.TYPE,
            line=type_type_ctx.start.line,
            code=getOriginalCodeText(type_type_ctx),
            shared_id=self.calculate_shared_id(type_type_ctx)
        )
        self.ast.add_edge(cast_node, type_node)

        self.parentStack.push(cast_node)
        self.visit(ctx.expression())
        self.parentStack.peek()

        # return "(" + getOriginalCodeText(ctx.typeType()) + ") " + self.visit(ctx.expression())

    def visitExprPostUnaryOp(self, ctx: JavaParser.ExprPostUnaryOpContext):
        # expression postfix=('++' | '--')                 # ExprPostUnaryOp

        node = self.add_node(
            kind=ASNodeKind.UNARY,
            line=ctx.start.line,
            code=ctx.postfix.text,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), node)
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

    def visitUnaryExpression(self, op_ctx: JavaParser.ExprPrePreUnaryOpContext | JavaParser.ExprNegationContext, op_text=None):
        op_node = self.add_node(
            kind=ASNodeKind.UNARY,
            line=op_ctx.start.line,
            code=op_text or op_ctx.prefix.text,
            shared_id=self.calculate_shared_id(op_ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), op_node)
        self.parentStack.push(op_node)
        self.visit(op_ctx.expression())
        self.parentStack.pop()

    def visitBinaryExpression(self, op_ctx: BinaryOperationContext, op_text: str | None = None):
        op_node = self.add_node(
            kind=ASNodeKind.BOP,
            line=op_ctx.start.line,
            code=op_text or op_ctx.bop.text,
            shared_id=self.calculate_shared_id(op_ctx.bop)
        )
        self.ast.add_edge(self.parentStack.peek(), op_node)
        self.parentStack.push(op_node)
        self.visit(op_ctx.expression(0))  # left expression
        self.visit(op_ctx.expression(1))  # right expression
        self.parentStack.pop()

    def visitExprAddSub(self, ctx: JavaParser.ExprAddSubContext):
        # expression bop=('+'|'-') expression              # ExprAddSub

        # addSubNode = ASNode(ASNodeKind.ARITH)
        # addSubNode.setLineOfCode(ctx.start.line)
        # addSubNode.setCode(ctx.bop.text)
        # addSubNode.setSharedId(ctx)
        # self.add_node(addSubNode)
        # self.ast.add_edge(self.parentStack.peek(), None, addSubNode))
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
        self.visitBinaryExpression(ctx, op_text=bop)

    def visitExprComparison(self, ctx: JavaParser.ExprComparisonContext):
        # expression bop=('<=' | '>=' | '>' | '<') expression
        # opNode = ASNode(ASNodeKind.BOP)
        # opNode.setLineOfCode(ctx.start.line)
        # opNode.setCode(ctx.bop.text)
        # opNode.setSharedId(ctx)
        # self.add_node(opNode)
        # self.ast.add_edge(self.parentStack.peek(), None, opNode))
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
        # self.add_node(opNode)
        # self.ast.add_edge(self.parentStack.peek(), None, opNode))
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

        ternary_node = self.add_node(
            kind=ASNodeKind.TERNARY,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), ternary_node)

        predicate_node = self.add_node(
            kind=ASNodeKind.TERNARY_PREDICATE,
            line=ctx.start.line,  # TODO: различать с тернарной нодой
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), predicate_node)
        self.parentStack.push(predicate_node)
        self.visit(ctx.expression(0))
        self.parentStack.pop()

        true_node = self.add_node(
            kind=ASNodeKind.TERNARY_TRUE,
            line=ctx.start.line,  # TODO: различать с тернарной нодой
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), true_node)
        self.parentStack.push(true_node)
        self.visit(ctx.expression(1))
        self.parentStack.pop()

        false_node = self.add_node(
            kind=ASNodeKind.TERNARY_FALSE,
            line=ctx.start.line,  # TODO: различать с тернарной нодой
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), false_node)
        self.parentStack.push(false_node)
        self.visit(ctx.expression(2))
        self.parentStack.pop()

    def visitExprAssign(self, ctx: JavaParser.ExprAssignContext):
        # <assoc=right> expression
        #       bop=('=' | '+=' | '-=' | '*=' | '/=' | '&=' | '|=' | '^=' | '>>=' | '>>>=' | '<<=' | '%=')
        #       expression

        assign_node = self.add_node(
            kind=ASNodeKind.ASSIGN,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx),
            optional_properties=dict(assignmentExpression=getOriginalCodeText(ctx.expression(1)))
        )
        self.ast.add_edge(self.parentStack.peek(), assign_node)

        left_expr_ctx = ctx.expression(0)
        left_node = self.add_node(
            kind=ASNodeKind.ASSIGN_LEFT,
            line=left_expr_ctx.start.line,
            shared_id=self.calculate_shared_id(left_expr_ctx)
        )
        self.ast.add_edge(assign_node, left_node)
        self.parentStack.push(left_node)
        self.visit(left_expr_ctx)
        self.parentStack.pop()

        right_expr_ctx = ctx.expression(1)
        right_node = self.add_node(
            kind=ASNodeKind.ASSIGN_RIGHT,
            line=right_expr_ctx.start.line,
            shared_id=self.calculate_shared_id(right_expr_ctx)
        )
        self.ast.add_edge(assign_node, right_node)
        self.parentStack.push(right_node)
        self.visit(right_expr_ctx)
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

        array_init = self.add_node(
            kind=ASNodeKind.ARRAY_INIT,
            line=ctx.start.line,
            shared_id=self.calculate_shared_id(ctx)
        )
        self.ast.add_edge(self.parentStack.peek(), array_init)
        self.parentStack.push(array_init)
        if ctx.variableInitializer() is not None:
            # arrayInitializerStr = "{ "
            # for varInitCtx in ctx.variableInitializer():
            #     arrayInitializerStr += ", " + self.visit(varInitCtx)
            # return arrayInitializerStr
            for var_init_ctx in ctx.variableInitializer():
                self.visit(var_init_ctx)
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

    def calculate_shared_id(self, ctx):
        return getIdByCtx(ctx, self.filename)

    def add_node(self, kind: ASNodeKind, line: int, code: str = "", shared_id: str = None, optional_properties: dict[str, any] = None) -> ASNode:
        return self.ast.add_node(
            kind=kind,
            code=code,
            line=line,
            shared_id=shared_id,
            file=self.filename,
            optional_properties=optional_properties
        )
