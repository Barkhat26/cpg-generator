from pathlib import Path

from graphs.cfg.block import Block
from graphs.cfg.cfg_edge import CFEdgeKind
from graphs.cfg.cfg_node import CFNode, CFNodeKind
from graphs.cfg.control_flow_graph_nx import ControlFlowGraphNX
from utils.datatypes import Queue, Stack
from utils.other import build_method_qn
from utils.parsing import getOriginalCodeText, getIdByCtx
from log import cfg_visitor_logger as logger
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor



class CFGVisitor(JavaParserVisitor):
    def __init__(self, cfg: ControlFlowGraphNX, file_path: Path | str = None):
        self.cfg = cfg
        self.filePath = file_path
        self.preNodes = Stack(CFNode)
        self.preEdgeKinds = Stack(CFEdgeKind)
        self.loopBlocks = Stack(Block)
        self.labeledBlocks = []
        self.tryBlocks = Queue(Block)
        self.classNames = Stack(str)
        self.dontPop = False
        self.casesQueue = Queue(CFNode)

        self.currentMethodName: str | None = None
        self.packageName: str | None = None

    def init(self):
        self.preNodes.clear()
        self.preNodes.clear()
        self.loopBlocks.clear()
        self.labeledBlocks.clear()
        self.tryBlocks.clear()
        self.dontPop = False
        self.currentMethodName = None

    def visitPackageDeclaration(self, ctx:JavaParser.PackageDeclarationContext):
        # packageDeclaration: annotation* PACKAGE qualifiedName ';'
        self.packageName = ctx.qualifiedName().getText()

    def visitClassDeclaration(self, ctx:JavaParser.ClassDeclarationContext):
        # classDeclaration
        #     : CLASS IDENTIFIER typeParameters?
        #       (EXTENDS typeType)?
        #       (IMPLEMENTS typeList)?
        #       classBody
        self.classNames.push(ctx.IDENTIFIER().getText())
        self.visit(ctx.classBody())
        self.classNames.pop()
        return None

    def visitClassBodyDeclaration(self, ctx:JavaParser.ClassBodyDeclarationContext):
        # classBodyDeclaration: ';' | STATIC? block | modifier* memberDeclaration
        # if ctx.block() is not None:
        #     self.init()

        return self.visitChildren(ctx)

    def visitConstructorDeclaration(self, ctx:JavaParser.ConstructorDeclarationContext):
        # constructorDeclaration: IDENTIFIER formalParameters (THROWS qualifiedNameList)? constructorBody=block

        self.init()

        self.currentMethodName = ctx.IDENTIFIER().getText()
        entry = self.cfg.add_node(
            kind=CFNodeKind.ENTRY,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=ctx.IDENTIFIER().getText() + getOriginalCodeText(ctx.formalParameters()),
            shared_id=self.calculate_shared_id(ctx),
            optional_properties={'name': self.currentMethodName, 'class': self.classNames.peek()}
        )
        qualified_name = build_method_qn(self.packageName, self.classNames.peek(), self.currentMethodName)
        self.cfg.add_entry_node(qualified_name, entry)

        self.preNodes.push(entry)
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        logger.info(f"Building CFG for {qualified_name} method...")
        self.visitChildren(ctx)
        self.currentMethodName = None

    def visitMethodDeclaration(self, ctx:JavaParser.MethodDeclarationContext):
        # methodDeclaration
        #     : typeTypeOrVoid IDENTIFIER formalParameters ('[' ']')*
        #       (THROWS qualifiedNameList)?
        #       methodBody

        self.init()

        self.currentMethodName = ctx.IDENTIFIER().getText()
        ret_type = ctx.typeTypeOrVoid().getText()
        entry = self.cfg.add_node(
            kind=CFNodeKind.ENTRY,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=ret_type + " " + ctx.IDENTIFIER().getText() + getOriginalCodeText(ctx.formalParameters()),
            shared_id=self.calculate_shared_id(ctx),
            optional_properties={
                'name': self.currentMethodName,
                'class': self.classNames.peek(),
                'type': ret_type
            }
        )
        qualified_name = build_method_qn(self.packageName, self.classNames.peek(), self.currentMethodName)
        self.cfg.add_entry_node(qualified_name, entry)

        self.preNodes.push(entry)
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        logger.info(f"Building CFG for {qualified_name} method...")
        self.visitChildren(ctx)
        self.currentMethodName = None

    # def visitMethodBody(self, ctx:JavaParser.MethodBodyContext):
    #     entry = CFNode(CFNodeKind.ENTRY, "")
    #
    #     self.currentCFG.addNode(entry)
    #     self.preEdges.push(CFEdgeKind.EPS)
    #     self.preNodes.push(entry)
    #     self.visitChildren(ctx)

    def visitLocalVariableDeclaration(self, ctx:JavaParser.LocalVariableDeclarationContext):
        # localVariableDeclaration: variableModifier* typeType variableDeclarators
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?

        for varCtx in ctx.variableDeclarators().variableDeclarator():
            declarator = self.addNodeAndPreEdge(
                kind=CFNodeKind.ASSIGN,
                line=varCtx.start.line,
                file=self.filePath,
                method=self.currentMethodName,
                code=ctx.typeType().getText() + " " + getOriginalCodeText(varCtx) + ";",
                shared_id=self.calculate_shared_id(varCtx))
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(declarator)
        return None

    def visitStmtIf(self, ctx:JavaParser.StmtIfContext):
        # IF parExpression trueClause=statement (ELSE falseClause=statement)?

        if_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.IF,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="if " + getOriginalCodeText(ctx.parExpression()),
            shared_id=self.calculate_shared_id(ctx)
        )

        self.preEdgeKinds.push(CFEdgeKind.TRUE)
        self.preNodes.push(if_node)

        self.visit(ctx.trueClause)

        end_if = self.addNodeAndPreEdge(
            kind=CFNodeKind.IF_END,
            file=self.filePath,
            method=self.currentMethodName,
            line=ctx.start.line,
            code="endif"
        )

        if not ctx.falseClause:
            self.cfg.add_edge(if_node, end_if, CFEdgeKind.FALSE)
        else:
            self.preEdgeKinds.push(CFEdgeKind.FALSE)
            self.preNodes.push(if_node)
            self.visit(ctx.falseClause)
            self.popAddPreEdgeTo(end_if)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(end_if)
        return

    def visitStmtFor(self, ctx:JavaParser.StmtForContext):
        # statement: FOR '(' forControl ')' statement

        if (enhanced_for_ctx := ctx.forControl().enhancedForControl()) is not None:
            # enhancedForControl: variableModifier* typeType variableDeclaratorId ':' expression

            for_expr = self.addNodeAndPreEdge(
                kind=CFNodeKind.FOR_EXPR,
                line=enhanced_for_ctx.start.line,
                file=self.filePath,
                method=self.currentMethodName,
                code="for (" + getOriginalCodeText(enhanced_for_ctx) + ")",
                shared_id=self.calculate_shared_id(enhanced_for_ctx)
            )
            for_end = self.cfg.add_node(
                kind=CFNodeKind.FOR_END,
                file=self.filePath,
                method=self.currentMethodName,
                code="endfor"
            )
            self.cfg.add_edge(for_expr, for_end, CFEdgeKind.FALSE)

            self.preEdgeKinds.push(CFEdgeKind.TRUE)
            self.preNodes.push(for_expr)

            self.loopBlocks.push(Block(for_expr, for_end))
            self.visit(ctx.statement())
            self.loopBlocks.pop()
            self.popAddPreEdgeTo(for_expr)

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(for_end)
        else:
            # forInit? ';' expression? ';' forUpdate=expressionList?

            if (for_init_ctx := ctx.forControl().forInit()) is not None:
                for_init = self.addNodeAndPreEdge(
                    kind=CFNodeKind.FOR_INIT,
                    line=for_init_ctx.start.line,
                    file=self.filePath,
                    method=self.currentMethodName,
                    code=getOriginalCodeText(for_init_ctx),
                    shared_id=self.calculate_shared_id(for_init_ctx)
                )
            else:
                for_init = None

            if (for_expr_ctx := ctx.forControl().expression()) is not None:
                for_expr_line = for_expr_ctx.start.line
                for_expr_code = "for (" + getOriginalCodeText(for_expr_ctx) + ")"
                for_expr_shared_id = self.calculate_shared_id(for_expr_ctx)
            else:
                for_expr_line = ctx.forControl().start.line
                for_expr_code = "for ( ; )"
                for_expr_shared_id = None

            for_expr = self.cfg.add_node(
                kind=CFNodeKind.FOR_EXPR,
                line=for_expr_line,
                file=self.filePath,
                method=self.currentMethodName,
                code=for_expr_code,
                shared_id=for_expr_shared_id
            )

            if for_init is not None:
                self.cfg.add_edge(for_init, for_expr)
            else:
                self.popAddPreEdgeTo(for_expr)

            if ctx.forControl().forUpdate is None:
                for_update_line = ctx.forControl().start.line
                for_update_code = " ; "
                for_update_shared_id = None
            else:
                for_update_ctx = ctx.forControl().forUpdate
                for_update_line = for_update_ctx.start.line
                for_update_code = getOriginalCodeText(for_update_ctx)
                for_update_shared_id = self.calculate_shared_id(for_update_ctx)

            for_update = self.cfg.add_node(
                kind=CFNodeKind.FOR_UPDATE,
                line=for_update_line,
                file=self.filePath,
                method=self.currentMethodName,
                code=for_update_code,
                shared_id=for_update_shared_id
            )

            for_end = self.cfg.add_node(
                kind=CFNodeKind.FOR_END,
                file=self.filePath,
                method=self.currentMethodName,
                code="endfor"
            )
            self.cfg.add_edge(for_expr, for_end, CFEdgeKind.FALSE)

            self.preEdgeKinds.push(CFEdgeKind.TRUE)
            self.preNodes.push(for_expr)

            self.loopBlocks.push(Block(for_update, for_end))
            self.visit(ctx.statement())
            self.loopBlocks.pop()

            self.popAddPreEdgeTo(for_update)
            self.cfg.add_edge(for_update, for_expr)

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(for_end)

        return None

    def visitStmtWhile(self, ctx:JavaParser.StmtWhileContext):
        # statement: WHILE parExpression statement

        while_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.WHILE,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="while " + getOriginalCodeText(ctx.parExpression()),
            shared_id=self.calculate_shared_id(ctx)
        )
        end_while = self.cfg.add_node(
            kind=CFNodeKind.WHILE_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="endwhile"
        )
        self.cfg.add_edge(while_node, end_while, CFEdgeKind.FALSE)

        self.preEdgeKinds.push(CFEdgeKind.TRUE)
        self.preNodes.push(while_node)

        self.loopBlocks.push(Block(while_node, end_while))
        self.visit(ctx.statement())
        self.loopBlocks.pop()

        self.popAddPreEdgeTo(while_node)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(end_while)
        return None

    def visitStmtDoWhile(self, ctx:JavaParser.StmtDoWhileContext):
        # statement: DO statement WHILE parExpression ';'

        do_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.DO_WHILE,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="do"
        )

        while_node = self.cfg.add_node(
            kind=CFNodeKind.WHILE,
            line=ctx.parExpression().start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="while " + getOriginalCodeText(ctx.parExpression()),
            shared_id=self.calculate_shared_id(ctx)
        )

        do_while_end = self.cfg.add_node(
            kind=CFNodeKind.DO_WHILE_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="end-do-while"
        )

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(do_node)

        self.loopBlocks.push(Block(while_node, do_while_end))
        self.visit(ctx.statement())
        self.loopBlocks.pop()

        self.popAddPreEdgeTo(while_node)
        self.cfg.add_edge(while_node, do_node, CFEdgeKind.TRUE)  # TODO: может перенести эти 2 add_edge наверх?
        self.cfg.add_edge(while_node, do_while_end, CFEdgeKind.FALSE)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(do_while_end)
        return None

    def visitStmtSwitch(self, ctx:JavaParser.StmtSwitchContext):
        # statement: SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'

        switch_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.SWITCH,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="switch " + getOriginalCodeText(ctx.parExpression()),
            shared_id=self.calculate_shared_id(ctx)
        )

        end_switch = self.cfg.add_node(
            kind=CFNodeKind.SWITCH_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="end-switch"
        )

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(switch_node)
        self.loopBlocks.push(Block(switch_node, end_switch))

        pre_case = None
        for grp in ctx.switchBlockStatementGroup():
            # switchBlockStatementGroup: switchLabel+ blockStatement+

            pre_case = self.visitSwitchLabels(grp.switchLabel(), pre_case)
            for blk in grp.blockStatement():
                self.visit(blk)
        pre_case = self.visitSwitchLabels(ctx.switchLabel(), pre_case)
        self.loopBlocks.pop()
        self.popAddPreEdgeTo(end_switch)
        if pre_case is not None:
            self.cfg.add_edge(pre_case, end_switch, CFEdgeKind.FALSE)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(end_switch)
        return None

    def visitSwitchLabels(self, lst: list[JavaParser.SwitchLabelContext], pre_case: CFNode) -> CFNode:
        case_stmt = pre_case

        for ctx in lst:
            case_stmt = self.cfg.add_node(
                kind=CFNodeKind.CASE_STMT,
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethodName,
                code=getOriginalCodeText(ctx)
            )

            if self.dontPop:
                self.dontPop = False
            else:
                self.cfg.add_edge(self.preNodes.pop(), case_stmt, self.preEdgeKinds.pop())

            if pre_case is not None:
                self.cfg.add_edge(pre_case, case_stmt, CFEdgeKind.FALSE)

            if ctx.getText() == "default":
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(case_stmt)
                case_stmt = None
            else:
                self.dontPop = True
                self.casesQueue.push(case_stmt)
                pre_case = case_stmt

        return case_stmt

    def visitStmtLabel(self, ctx:JavaParser.StmtLabelContext):
        # statement: identifierLabel=IDENTIFIER ':' statement

        # For each visited label-block, a Block object is created with
        # the current node as the start, and a dummy node as the end.
        # The newly created label-block is stored in an ArrayList of Blocks.
        label_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.LABEL,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=ctx.IDENTIFIER().getText() + ": ",
            shared_id=self.calculate_shared_id(ctx)
        )

        end_label_node = self.cfg.add_node(
            kind=CFNodeKind.LABEL_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="end-label"
        )

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(label_node)
        self.labeledBlocks.append(Block(label_node, end_label_node, ctx.IDENTIFIER().getText()))
        self.visit(ctx.statement())
        self.popAddPreEdgeTo(end_label_node)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(end_label_node)
        return None

    def visitStmtReturn(self, ctx:JavaParser.StmtReturnContext):
        # statement: RETURN expression? ';'

        self.addNodeAndPreEdge(
            kind=CFNodeKind.RET,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=getOriginalCodeText(ctx),
            shared_id=self.calculate_shared_id(ctx)
        )
        self.dontPop = True
        return None

    def visitStmtBreak(self, ctx:JavaParser.StmtBreakContext):
        # statement: BREAK IDENTIFIER? ';'

        # if a label is specified, search for the corresponding block in the labels-list,
        # and create an epsilon edge to the end of the labeled-block; else
        # create an epsilon edge to the end of the loop-block on top of the loopBlocks stack.
        break_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.BREAK,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=getOriginalCodeText(ctx),
            shared_id=self.calculate_shared_id(ctx)
        )

        if ctx.IDENTIFIER() is not None:
            for block in self.labeledBlocks:
                if block.label == ctx.IDENTIFIER().getText():
                    self.cfg.add_edge(break_node, block.end)
        else:
            block = self.loopBlocks.peek()
            self.cfg.add_edge(break_node, block.end)

        self.dontPop = True
        return None

    def visitStmtContinue(self, ctx:JavaParser.StmtContinueContext):
        # statement: CONTINUE IDENTIFIER? ';'

        # if a label is specified, search for the corresponding block in the labels-list,
        # and create an epsilon edge to the start of the labeled-block; else
        # create an epsilon edge to the start of the loop-block on top of the loopBlocks stack.
        continue_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.CONTINUE,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=getOriginalCodeText(ctx),
            shared_id=self.calculate_shared_id(ctx)
        )

        if ctx.IDENTIFIER() is not None:
            for block in self.labeledBlocks:
                if block.label == ctx.IDENTIFIER().getText():
                    self.cfg.add_edge(continue_node, block.start)
                    break
        else:
            block = self.loopBlocks.peek()
            self.cfg.add_edge(continue_node, block.start)

        self.dontPop = True
        return None

    def visitStmtSynchronized(self, ctx:JavaParser.StmtSynchronizedContext):
        # statement: SYNCHRONIZED parExpression block

        sync_stmt = self.addNodeAndPreEdge(
            kind=CFNodeKind.SYNC,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="synchronized " + getOriginalCodeText(ctx.parExpression()),
            shared_id=self.calculate_shared_id(ctx)
        )

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(sync_stmt)
        self.visit(ctx.block())

        end_sync_block = self.addNodeAndPreEdge(
            kind=CFNodeKind.SYNC_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="end-synchronized"
        )

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(end_sync_block)
        return None

    def visitStmtTry(self, ctx:JavaParser.StmtTryContext):
        # statement: TRY block (catchClause+ finallyBlock? | finallyBlock)

        try_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.TRY,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="try",
            shared_id=self.calculate_shared_id(ctx)
        )

        end_try = self.cfg.add_node(
            kind=CFNodeKind.TRY_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="end-try"
        )

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(try_node)
        self.tryBlocks.push(Block(try_node, end_try))
        self.visit(ctx.block())
        self.popAddPreEdgeTo(end_try)

        # If there is a finally-block, visit it first
        if (finally_block_ctx := ctx.finallyBlock()) is not None:
            finally_node = self.cfg.add_node(
                kind=CFNodeKind.FINALLY,
                line=finally_block_ctx.start.line,
                file=self.filePath,
                method=self.currentMethodName,
                code="finally",
                shared_id=self.calculate_shared_id(finally_block_ctx)
            )
            self.cfg.add_edge(end_try, finally_node)

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(finally_node)
            self.visit(ctx.finallyBlock().block())

            end_finally = self.addNodeAndPreEdge(
                kind=CFNodeKind.FINALLY_END,
                file=self.filePath,
                method=self.currentMethodName,
                code="end-finally"
            )
        else:
            finally_node = None
            end_finally = None


        # Now visit any available catch clauses
        if (catch_clause_ctx := ctx.catchClause()) is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block

            end_catch = self.cfg.add_node(
                kind=CFNodeKind.CATCH_END,
                file=self.filePath,
                method=self.currentMethodName,
                code="end-catch"
            )

            for cx in catch_clause_ctx:
                # connect the try-node to all catch-nodes;
                # create a single end-catch for all catch-blocks;
                catch_node = self.cfg.add_node(
                    kind=CFNodeKind.CATCH,
                    line=cx.start.line,
                    file=self.filePath,
                    method=self.currentMethodName,
                    code="catch (" + cx.catchType().getText() + " " + cx.IDENTIFIER().getText() + ")",
                    shared_id=self.calculate_shared_id(cx)
                )
                self.cfg.add_edge(end_try, catch_node, CFEdgeKind.THROWS)

                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(catch_node)
                self.visit(cx.block())
                self.popAddPreEdgeTo(end_catch)

            if finally_node is not None:
                # connect end-catch node to finally-node,
                # and push end-finally to the stack ...
                self.cfg.add_edge(end_catch, finally_node)
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(end_finally)
            else:
                # connect end-catch node to end-try,
                # and push end-try to the stack ...
                self.cfg.add_edge(end_catch, end_try)
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(end_try)
        else:
            # No catch-clause; it's a try-finally
            # push end-finally to the stack ...
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(end_finally)

        return None

    def visitStmtTryResource(self, ctx:JavaParser.StmtTryResourceContext):
        # statement: TRY resourceSpecification block catchClause* finallyBlock?
        # resourceSpecification: '(' resources ';'? ')'
        # resources: resource (';' resource)*
        # resource: variableModifier* classOrInterfaceType variableDeclaratorId '=' expression

        # TODO: избавиться от дублирования (в visitStmtTry почти то же самое)

        try_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.TRY,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="try",
            shared_id=self.calculate_shared_id(ctx)
        )
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(try_node)

        for rsrcCtx in ctx.resourceSpecification().resources().resource():
            resource = self.addNodeAndPreEdge(
                kind=CFNodeKind.RESOURCE,
                line=rsrcCtx.start.line,
                file=self.filePath,
                method=self.currentMethodName,
                code=getOriginalCodeText(rsrcCtx),
                shared_id=self.calculate_shared_id(rsrcCtx)
            )
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(resource)

        end_try = self.cfg.add_node(
            kind=CFNodeKind.TRY_END,
            file=self.filePath,
            method=self.currentMethodName,
            code="end-try"
        )

        self.tryBlocks.push(Block(try_node, end_try))
        self.visit(ctx.block())
        self.popAddPreEdgeTo(end_try)

        # If there is a finally-block, visit it first
        if (finally_block_ctx := ctx.finallyBlock()) is not None:
            finally_node = self.cfg.add_node(
                kind=CFNodeKind.FINALLY,
                line=finally_block_ctx.start.line,
                file=self.filePath,
                method=self.currentMethodName,
                code="finally",
                shared_id=self.calculate_shared_id(finally_block_ctx)
            )
            self.cfg.add_edge(end_try, finally_node)

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(finally_node)
            self.visit(ctx.finallyBlock().block())

            end_finally = self.addNodeAndPreEdge(
                kind=CFNodeKind.FINALLY_END,
                file=self.filePath,
                method=self.currentMethodName,
                code="end-finally"
            )
        else:
            finally_node = None
            end_finally = None

        # Now visit any available catch clauses
        if (catch_clause_ctx := ctx.catchClause()) is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block

            end_catch = self.cfg.add_node(
                kind=CFNodeKind.CATCH_END,
                file=self.filePath,
                method=self.currentMethodName,
                code="end-catch"
            )

            for cx in catch_clause_ctx:
                # connect the try-node to all catch-nodes;
                # create a single end-catch for all catch-blocks;
                catch_node = self.cfg.add_node(
                    kind=CFNodeKind.CATCH,
                    line=cx.start.line,
                    file=self.filePath,
                    method=self.currentMethodName,
                    code="catch (" + cx.catchType().getText() + " " + cx.IDENTIFIER().getText() + ")",
                    shared_id=self.calculate_shared_id(cx)
                )
                self.cfg.add_edge(end_try, catch_node, CFEdgeKind.THROWS)

                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(catch_node)
                self.visit(cx.block())
                self.popAddPreEdgeTo(end_catch)

            if finally_node is not None:
                # connect end-catch node to finally-node,
                # and push end-finally to the stack ...
                self.cfg.add_edge(end_catch, finally_node)
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(end_finally)
            else:
                # connect end-catch node to end-try,
                # and push end-try to the stack ...
                self.cfg.add_edge(end_catch, end_try)
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(end_try)
        else:
            # No catch-clause; it's a try-finally
            # push end-finally to the stack ...
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(end_finally)

        return None

    def visitStmtThrow(self, ctx:JavaParser.StmtThrowContext):
        # statement: THROW expression ';'

        throw_node = self.addNodeAndPreEdge(
            kind=CFNodeKind.THROW,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code="throw " + getOriginalCodeText(ctx.expression()),
            shared_id=self.calculate_shared_id(ctx)
        )

        if not self.tryBlocks.isEmpty():
            try_block = self.tryBlocks.peek()
            self.cfg.add_edge(throw_node, try_block.end, CFEdgeKind.THROWS)
        else:
            # do something when it's a throw not in a try-catch block ...
            # in such a situation, the method declaration has a throws clause;
            # so we should create a special node for the method-throws,
            # and create an edge from this throw-statement to that throws-node.
            pass

        self.dontPop = True
        return None

    # def visitSwitchLabel(self, ctx:JavaParser.SwitchLabelContext):
    #     # switchLabel: CASE (constantExpression=expression | enumConstantName=IDENTIFIER) ':' | DEFAULT ':'
    #     pass



    def visitStmtExpr(self, ctx:JavaParser.StmtExprContext):
        # statementExpression=expression ';'

        expr = self.addNodeAndPreEdge(
            kind=CFNodeKind.EXPR,
            line=ctx.start.line,
            file=self.filePath,
            method=self.currentMethodName,
            code=getOriginalCodeText(ctx),
            shared_id=self.calculate_shared_id(ctx)
        )
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(expr)
        return None

    def addNodeAndPreEdge(self, kind: CFNodeKind, line: int = 0, file: str | None = None, method: str | None = None, code: str = "", shared_id: str = None, optional_properties: dict[str, any] = None) -> CFNode:
        # Добавляет узел в CFG и пристыковывает к нему ребро
        node = self.cfg.add_node(
            kind=kind,
            line=line,
            file=file,
            method=method,
            code=code,
            shared_id=shared_id,
            optional_properties=optional_properties
        )
        self.popAddPreEdgeTo(node)
        return node

    def popAddPreEdgeTo(self, node: CFNode) -> None:
        # Создает ребро между предыдущим узлом и узлом 'node'.
        # Тип ребра извлекается из очереди 'preEdgeKinds'
        if self.dontPop:
            self.dontPop = False
        else:
            src = self.preNodes.pop()
            edge_kind = self.preEdgeKinds.pop()
            self.cfg.add_edge(src, node, edge_kind)

        for i in range(self.casesQueue.size(), 0, -1):
            self.cfg.add_edge(self.casesQueue.pop(), node, CFEdgeKind.TRUE)

    def calculate_shared_id(self, ctx):
        return getIdByCtx(ctx, self.filePath)
