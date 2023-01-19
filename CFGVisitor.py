import logging
from typing import List

from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from graphs.cfg.Block import Block
from graphs.cfg.CFEdge import CFEdgeKind, CFEdge
from graphs.cfg.CFNode import CFNode, CFNodeKind
from graphs.cfg.ControlFlowGraph import ControlFlowGraph
from utils import Queue, getOriginalCodeText, Stack

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

class CFGVisitor(JavaParserVisitor):
    def __init__(self, cfgs: List[ControlFlowGraph], filePath: str):
        self.cfgs = cfgs
        self.filePath = filePath
        self.preNodes = Stack()
        self.preEdgeKinds = Stack()
        self.loopBlocks = Stack()
        self.labeledBlocks = []
        self.tryBlocks = Queue()
        self.classNames = Stack()
        self.dontPop = False
        self.casesQueue = Queue()

        self.currentCFG = None
        self.currentMethodName = None
        self.packageName = None

    def init(self):
        self.preNodes.clear()
        self.preNodes.clear()
        self.loopBlocks.clear()
        self.labeledBlocks.clear()
        self.tryBlocks.clear()
        self.dontPop = False
        self.currentCFG = None
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
        entry = CFNode(CFNodeKind.ENTRY)
        entry.setLineOfCode(ctx.start.line)
        entry.setFile(self.filePath)
        args = getOriginalCodeText(ctx.formalParameters())
        entry.setCode(ctx.IDENTIFIER().getText() + args)
        entry.setSharedId(ctx)
        self.currentCFG = ControlFlowGraph()
        self.currentMethodName = ctx.IDENTIFIER().getText()
        self.currentCFG.setProperty("className", self.classNames.peek())
        self.currentCFG.setProperty("methodName", self.currentMethodName)
        self.currentCFG.addVertex(entry)
        entry.setOptionalProperty("name", ctx.IDENTIFIER().getText())
        entry.setOptionalProperty("class", self.classNames.peek())

        self.preNodes.push(entry)
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.visitChildren(ctx)
        qualifiedName = f"{self.packageName}.{self.classNames.peek()}.{self.currentMethodName}"
        logger.info(f"Building CFG for {qualifiedName} method...")
        self.cfgs[qualifiedName] = self.currentCFG
        self.currentCFG = None
        self.currentMethodName = None

    def visitMethodDeclaration(self, ctx:JavaParser.MethodDeclarationContext):
        # methodDeclaration
        #     : typeTypeOrVoid IDENTIFIER formalParameters ('[' ']')*
        #       (THROWS qualifiedNameList)?
        #       methodBody

        self.init()
        entry = CFNode(CFNodeKind.ENTRY)
        entry.setLineOfCode(ctx.start.line)
        entry.setFile(self.filePath)
        retType = ctx.typeTypeOrVoid().getText()
        args = getOriginalCodeText(ctx.formalParameters())
        entry.setCode(retType + " " + ctx.IDENTIFIER().getText() + args)
        entry.setSharedId(ctx)
        self.currentCFG = ControlFlowGraph()
        self.currentMethodName = ctx.IDENTIFIER().getText()
        self.currentCFG.setProperty("className", self.classNames.peek())
        self.currentCFG.setProperty("methodName", self.currentMethodName)
        self.currentCFG.addVertex(entry)
        entry.setOptionalProperty("name", ctx.IDENTIFIER().getText())
        entry.setOptionalProperty("class", self.classNames.peek())
        entry.setOptionalProperty("type", retType)

        self.preNodes.push(entry)
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.visitChildren(ctx)
        qualifiedName = f"{self.packageName}.{self.classNames.peek()}.{self.currentMethodName}"
        logger.info(f"Building CFG for {qualifiedName} method...")
        self.cfgs[qualifiedName] = self.currentCFG
        self.currentCFG = None
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
            declr = CFNode(CFNodeKind.ASSIGN)
            declr.setLineOfCode(varCtx.start.line)
            declr.setFile(self.filePath)
            declr.setCode(ctx.typeType().getText() + " " + getOriginalCodeText(varCtx) + ";")
            declr.setSharedId(varCtx)
            self.addNodeAndPreEdge(declr)
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(declr)
        return None

    def visitStmtIf(self, ctx:JavaParser.StmtIfContext):
        # IF parExpression trueClause=statement (ELSE falseClause=statement)?

        ifNode = CFNode(CFNodeKind.IF)
        ifNode.setLineOfCode(ctx.start.line)
        ifNode.setFile(self.filePath)
        ifNode.setCode("if " + getOriginalCodeText(ctx.parExpression()))
        ifNode.setSharedId(ctx)
        self.addNodeAndPreEdge(ifNode)

        self.preEdgeKinds.push(CFEdgeKind.TRUE)
        self.preNodes.push(ifNode)

        self.visit(ctx.trueClause)

        endIf = CFNode(CFNodeKind.IF_END)
        endIf.setFile(self.filePath)
        endIf.setLineOfCode(ctx.start.line)
        endIf.setCode("endif")
        self.addNodeAndPreEdge(endIf)

        if not ctx.falseClause:
            self.currentCFG.addEdge(CFEdge(ifNode, CFEdgeKind.FALSE, endIf))
        else:
            self.preEdgeKinds.push(CFEdgeKind.FALSE)
            self.preNodes.push(ifNode)
            self.visit(ctx.falseClause)
            self.popAddPreEdgeTo(endIf)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(endIf)
        return

    def visitStmtFor(self, ctx:JavaParser.StmtForContext):
        # statement: FOR '(' forControl ')' statement
        if ctx.forControl().enhancedForControl() is not None:
            # enhancedForControl: variableModifier* typeType variableDeclaratorId ':' expression
            forExpr = CFNode(CFNodeKind.FOR_EXPR)
            forExpr.setLineOfCode(ctx.forControl().enhancedForControl().start.line)
            forExpr.setFile(self.filePath)
            forExpr.setCode("for (" + getOriginalCodeText(ctx.forControl().enhancedForControl()) + ")")
            forExpr.setSharedId(ctx.forControl().enhancedForControl())
            self.addNodeAndPreEdge(forExpr)

            forEnd = CFNode(CFNodeKind.FOR_END)
            forEnd.setLineOfCode(0)
            forEnd.setFile(self.filePath)
            forEnd.setCode("endfor")
            self.currentCFG.addVertex(forEnd)
            self.currentCFG.addEdge(CFEdge(forExpr, CFEdgeKind.FALSE, forEnd))

            self.preEdgeKinds.push(CFEdgeKind.TRUE)
            self.preNodes.push(forExpr)

            self.loopBlocks.push(Block(forExpr, forEnd))
            self.visit(ctx.statement())
            self.loopBlocks.pop()
            self.popAddPreEdgeTo(forExpr)

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(forEnd)
        else:
            # forInit? ';' expression? ';' forUpdate=expressionList?
            forInit = None
            if ctx.forControl().forInit() is not None:
                forInit = CFNode(CFNodeKind.FOR_INIT)
                forInit.setLineOfCode(ctx.forControl().forInit().start.line)
                forInit.setFile(self.filePath)
                forInit.setCode(getOriginalCodeText(ctx.forControl().forInit()))
                forInit.setSharedId(ctx.forControl().forInit())
                self.addNodeAndPreEdge(forInit)

            forExpr = CFNode(CFNodeKind.FOR_EXPR)
            if ctx.forControl().expression() is None:
                forExpr.setLineOfCode(ctx.forControl().start.line)
                forExpr.setFile(self.filePath)
                forExpr.setCode("for ( ; )")
            else:
                forExpr.setLineOfCode(ctx.forControl().expression().start.line)
                forExpr.setFile(self.filePath)
                forExpr.setCode("for (" + getOriginalCodeText(ctx.forControl().expression()) + ")")
                forExpr.setSharedId(ctx.forControl().expression())
            self.currentCFG.addVertex(forExpr)
            if forInit is not None:
                self.currentCFG.addEdge(CFEdge(forInit, CFEdgeKind.EPS, forExpr))
            else:
                self.popAddPreEdgeTo(forExpr)

            forUpdate = CFNode(CFNodeKind.FOR_UPDATE)
            if ctx.forControl().forUpdate is None:
                forUpdate.setLineOfCode(ctx.forControl().start.line)
                forUpdate.setFile(self.filePath)
                forUpdate.setCode(" ; ")
            else:
                forUpdate.setLineOfCode(ctx.forControl().forUpdate.start.line)
                forUpdate.setFile(self.filePath)
                forUpdate.setCode(getOriginalCodeText(ctx.forControl().forUpdate))
                forUpdate.setSharedId(ctx.forControl().forUpdate)

            self.currentCFG.addVertex(forUpdate)

            forEnd = CFNode(CFNodeKind.FOR_END)
            forEnd.setLineOfCode(0)
            forEnd.setFile(self.filePath)
            forEnd.setCode("endfor")
            self.currentCFG.addVertex(forEnd)
            self.currentCFG.addEdge(CFEdge(forExpr, CFEdgeKind.FALSE, forEnd))

            self.preEdgeKinds.push(CFEdgeKind.TRUE)
            self.preNodes.push(forExpr)

            self.loopBlocks.push(Block(forUpdate, forEnd))
            self.visit(ctx.statement())
            self.loopBlocks.pop()

            self.popAddPreEdgeTo(forUpdate)
            self.currentCFG.addEdge(CFEdge(forUpdate, CFEdgeKind.EPS, forExpr))

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(forEnd)

        return None

    def visitStmtWhile(self, ctx:JavaParser.StmtWhileContext):
        # statement: WHILE parExpression statement
        whileNode = CFNode(CFNodeKind.WHILE)
        whileNode.setLineOfCode(ctx.start.line)
        whileNode.setFile(self.filePath)
        whileNode.setCode("while " + getOriginalCodeText(ctx.parExpression()))
        whileNode.setSharedId(ctx)
        self.addNodeAndPreEdge(whileNode)

        endWhile = CFNode(CFNodeKind.WHILE_END)
        endWhile.setLineOfCode(0)
        endWhile.setFile(self.filePath)
        endWhile.setCode("endwhile")
        self.currentCFG.addVertex(endWhile)
        self.currentCFG.addEdge(CFEdge(whileNode, CFEdgeKind.FALSE, endWhile))

        self.preEdgeKinds.push(CFEdgeKind.TRUE)
        self.preNodes.push(whileNode)

        self.loopBlocks.push(Block(whileNode, endWhile))
        self.visit(ctx.statement())
        self.loopBlocks.pop()

        self.popAddPreEdgeTo(whileNode)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(endWhile)
        return None

    def visitStmtDoWhile(self, ctx:JavaParser.StmtDoWhileContext):
        # statement: DO statement WHILE parExpression ';'
        doNode = CFNode(CFNodeKind.DO_WHILE)
        doNode.setLineOfCode(ctx.start.line)
        doNode.setFile(self.filePath)
        doNode.setCode("do")
        self.addNodeAndPreEdge(doNode)

        whileNode = CFNode(CFNodeKind.WHILE)
        whileNode.setLineOfCode(ctx.parExpression().start.line)
        whileNode.setFile(self.filePath)
        whileNode.setCode("while " + getOriginalCodeText(ctx.parExpression()))
        whileNode.setSharedId(ctx)
        self.currentCFG.addVertex(whileNode)

        doWhileEnd = CFNode(CFNodeKind.DO_WHILE_END)
        doWhileEnd.setLineOfCode(0)
        doWhileEnd.setFile(self.filePath)
        doWhileEnd.setCode("end-do-while")
        self.currentCFG.addVertex(doWhileEnd)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(doNode)

        self.loopBlocks.push(Block(whileNode, doWhileEnd))
        self.visit(ctx.statement())
        self.loopBlocks.pop()

        self.popAddPreEdgeTo(whileNode)
        self.currentCFG.addEdge(CFEdge(whileNode, CFEdgeKind.TRUE, doNode))
        self.currentCFG.addEdge(CFEdge(whileNode, CFEdgeKind.FALSE, doWhileEnd))

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(doWhileEnd)
        return None

    def visitStmtSwitch(self, ctx:JavaParser.StmtSwitchContext):
        # statement: SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'
        switchNode = CFNode(CFNodeKind.SWITCH)
        switchNode.setLineOfCode(ctx)
        switchNode.setFile(self.filePath)
        switchNode.setCode("switch " + getOriginalCodeText(ctx.parExpression()))
        switchNode.setSharedId(ctx)
        self.addNodeAndPreEdge(switchNode)

        endSwitch = CFNode(CFNodeKind.SWITCH_END)
        endSwitch.setLineOfCode(0)
        endSwitch.setFile(self.filePath)
        endSwitch.setCode("end-switch")
        self.currentCFG.addVertex(endSwitch)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(switchNode)
        self.loopBlocks.push(Block(switchNode, endSwitch))

        preCase = None
        for grp in ctx.switchBlockStatementGroup():
            # switchBlockStatementGroup: switchLabel+ blockStatement+
            preCase = self.visitSwitchLabels(grp.switchLabel(), preCase)
            for blk in grp.blockStatement():
                self.visit(blk)
        preCase = self.visitSwitchLabels(ctx.switchLabel(), preCase)
        self.loopBlocks.pop()
        self.popAddPreEdgeTo(endSwitch)
        if preCase is not None:
            self.currentCFG.addEdge(CFEdge(preCase, CFEdgeKind.FALSE, endSwitch))

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(endSwitch)
        return None

    def visitSwitchLabels(self, lst: List[JavaParser.SwitchLabelContext], preCase: CFNode) -> CFNode:
        caseStmt = preCase
        for ctx in lst:
            caseStmt = CFNode(CFNodeKind.CASE_STMT)
            caseStmt.setLineOfCode(ctx.start.line)
            caseStmt.setFile(self.filePath)
            caseStmt.setCode(getOriginalCodeText(ctx))
            self.currentCFG.addVertex(caseStmt)
            if self.dontPop:
                self.dontPop = False
            else:
                self.currentCFG.addEdge(CFEdge(self.preNodes.pop(), self.preEdgeKinds.pop(), caseStmt))

            if preCase is not None:
                self.currentCFG.addEdge(CFEdge(preCase, CFEdgeKind.FALSE, caseStmt))

            if ctx.getText() == "default":
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(caseStmt)
                caseStmt = None
            else:
                self.dontPop = True
                self.casesQueue.push(caseStmt)
                preCase = caseStmt
        return caseStmt

    def visitStmtLabel(self, ctx:JavaParser.StmtLabelContext):
        # statement: identifierLabel=IDENTIFIER ':' statement
        # For each visited label-block, a Block object is created with
        # the the current node as the start, and a dummy node as the end.
        # The newly created label-block is stored in an ArrayList of Blocks.
        labelNode = CFNode(CFNodeKind.LABEL)
        labelNode.setLineOfCode(ctx.start.line)
        labelNode.setFile(self.filePath)
        labelNode.setCode(ctx.IDENTIFIER().getText() + ": ")
        labelNode.setSharedId(ctx)
        self.addNodeAndPreEdge(labelNode)

        endLabelNode = CFNode(CFNodeKind.LABEL_END)
        endLabelNode.setLineOfCode(0)
        endLabelNode.setFile(self.filePath)
        endLabelNode.setCode("end-label")
        self.currentCFG.addVertex(endLabelNode)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(labelNode)
        self.labeledBlocks.append(Block(labelNode, endLabelNode, ctx.IDENTIFIER().getText()))
        self.visit(ctx.statement())
        self.popAddPreEdgeTo(endLabelNode)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(endLabelNode)
        return None

    def visitStmtReturn(self, ctx:JavaParser.StmtReturnContext):
        # statement: RETURN expression? ';'
        ret = CFNode(CFNodeKind.RET)
        ret.setLineOfCode(ctx.start.line)
        ret.setFile(self.filePath)
        ret.setCode(getOriginalCodeText(ctx))
        ret.setSharedId(ctx)
        self.addNodeAndPreEdge(ret)
        self.dontPop = True
        return None

    def visitStmtBreak(self, ctx:JavaParser.StmtBreakContext):
        # statement: BREAK IDENTIFIER? ';'
        # if a label is specified, search for the corresponding block in the labels-list,
        # and create an epsilon edge to the end of the labeled-block; else
        # create an epsilon edge to the end of the loop-block on top of the loopBlocks stack.
        breakNode = CFNode(CFNodeKind.BREAK)
        breakNode.setLineOfCode(ctx.start.line)
        breakNode.setFile(self.filePath)
        breakNode.setCode(getOriginalCodeText(ctx))
        breakNode.setSharedId(ctx)
        self.addNodeAndPreEdge(breakNode)

        if ctx.IDENTIFIER() is not None:
            for block in self.labeledBlocks:
                if block.label == ctx.IDENTIFIER().getText():
                    self.currentCFG.addEdge(CFEdge(breakNode, CFEdgeKind.EPS, block.end))
        else:
            block = self.loopBlocks.peek()
            self.currentCFG.addEdge(CFEdge(breakNode, CFEdgeKind.EPS, block.end))

        self.dontPop = True
        return None

    def visitStmtContinue(self, ctx:JavaParser.StmtContinueContext):
        # statement: CONTINUE IDENTIFIER? ';'
        # if a label is specified, search for the corresponding block in the labels-list,
        # and create an epsilon edge to the start of the labeled-block; else
        # create an epsilon edge to the start of the loop-block on top of the loopBlocks stack.
        continueNode = CFNode(CFNodeKind.CONTINUE)
        continueNode.setLineOfCode(ctx.start.line)
        continueNode.setFile(self.filePath)
        continueNode.setCode(getOriginalCodeText(ctx))
        continueNode.setSharedId(ctx)
        self.addNodeAndPreEdge(continueNode)

        if ctx.IDENTIFIER() is not None:
            for block in self.labeledBlocks:
                if block.label == ctx.IDENTIFIER().getText():
                    self.currentCFG.addEdge(CFEdge(continueNode, CFEdgeKind.EPS, block.start))
                    break
        else:
            block = self.loopBlocks.peek()
            self.currentCFG.addEdge(CFEdge(continueNode, CFEdgeKind.EPS, block.start))

        self.dontPop = True
        return None

    def visitStmtSynchronized(self, ctx:JavaParser.StmtSynchronizedContext):
        # statement: SYNCHRONIZED parExpression block
        syncStmt = CFNode(CFNodeKind.SYNC)
        syncStmt.setLineOfCode(ctx.start.line)
        syncStmt.setFile(self.filePath)
        syncStmt.setCode("synchronized " + getOriginalCodeText(ctx.parExpression()))
        syncStmt.setSharedId(ctx)
        self.addNodeAndPreEdge(syncStmt)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(syncStmt)
        self.visit(ctx.block())

        endSyncBlock = CFNode(CFNodeKind.SYNC_END)
        endSyncBlock.setLineOfCode(0)
        endSyncBlock.setFile(self.filePath)
        endSyncBlock.setCode("end-synchronized")
        self.addNodeAndPreEdge(endSyncBlock)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(endSyncBlock)
        return None

    def visitStmtTry(self, ctx:JavaParser.StmtTryContext):
        # statement: TRY block (catchClause+ finallyBlock? | finallyBlock)
        tryNode = CFNode(CFNodeKind.TRY)
        tryNode.setLineOfCode(ctx.start.line)
        tryNode.setFile(self.filePath)
        tryNode.setCode("try")
        tryNode.setSharedId(ctx)
        self.addNodeAndPreEdge(tryNode)

        endTry = CFNode(CFNodeKind.TRY_END)
        endTry.setLineOfCode(0)
        endTry.setFile(self.filePath)
        endTry.setCode("end-try")
        self.currentCFG.addVertex(endTry)

        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(tryNode)
        self.tryBlocks.push(Block(tryNode, endTry))
        self.visit(ctx.block())
        self.popAddPreEdgeTo(endTry)

        # If there is a finally-block, visit it first
        finallyNode = None
        endFinally = None
        if ctx.finallyBlock() is not None:
            finallyNode = CFNode(CFNodeKind.FINALLY)
            finallyNode.setLineOfCode(ctx.finallyBlock().start.line)
            finallyNode.setFile(self.filePath)
            finallyNode.setCode("finally")
            finallyNode.setSharedId(ctx.finallyBlock())
            self.currentCFG.addVertex(finallyNode)
            self.currentCFG.addEdge(CFEdge(endTry, CFEdgeKind.EPS, finallyNode))

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(finallyNode)
            self.visit(ctx.finallyBlock().block())

            endFinally = CFNode(CFNodeKind.FINALLY_END)
            endFinally.setLineOfCode(0)
            endFinally.setFile(self.filePath)
            endFinally.setCode("end-finally")
            self.addNodeAndPreEdge(endFinally)

        # Now visit any available catch clauses
        if ctx.catchClause() is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            endCatch = CFNode(CFNodeKind.CATCH_END)
            endCatch.setLineOfCode(0)
            endCatch.setFile(self.filePath)
            endCatch.setCode("end-catch")
            self.currentCFG.addVertex(endCatch)

            for cx in ctx.catchClause():
                # connect the try-node to all catch-nodes;
                # create a single end-catch for all catch-blocks;
                catchNode = CFNode(CFNodeKind.CATCH)
                catchNode.setLineOfCode(cx.start.line)
                catchNode.setFile(self.filePath)
                catchNode.setCode("catch (" + cx.catchType().getText() + " " + cx.IDENTIFIER().getText() + ")")
                catchNode.setSharedId(cx)
                self.currentCFG.addVertex(catchNode)
                self.currentCFG.addEdge(CFEdge(endTry, CFEdgeKind.THROWS, catchNode))

                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(catchNode)
                self.visit(cx.block())
                self.popAddPreEdgeTo(endCatch)

            if finallyNode is not None:
                # connect end-catch node to finally-node,
                # and push end-finally to the stack ...
                self.currentCFG.addEdge(CFEdge(endCatch, CFEdgeKind.EPS, finallyNode))
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(endFinally)
            else:
                # connect end-catch node to end-try,
                # and push end-try to the the stack ...
                self.currentCFG.addEdge(CFEdge(endCatch, CFEdgeKind.EPS, endTry))
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(endTry)
        else:
            # No catch-clause; it's a try-finally
            # push end-finally to the stack ...
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(endFinally)

        return None

    def visitStmtTryResource(self, ctx:JavaParser.StmtTryResourceContext):
        # statement: TRY resourceSpecification block catchClause* finallyBlock?
        # resourceSpecification: '(' resources ';'? ')'
        # resources: resource (';' resource)*
        # resource: variableModifier* classOrInterfaceType variableDeclaratorId '=' expression
        tryNode = CFNode(CFNodeKind.TRY)
        tryNode.setLineOfCode(ctx.start.line)
        tryNode.setFile(self.filePath)
        tryNode.setCode("try")
        tryNode.setSharedId(ctx)
        self.addNodeAndPreEdge(tryNode)
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(tryNode)

        for rsrcCtx in ctx.resourceSpecification().resources().resource():
            resource = CFNode(CFNodeKind.RESOURCE)
            resource.setLineOfCode(rsrcCtx.start.line)
            resource.setFile(self.filePath)
            resource.setCode(getOriginalCodeText(rsrcCtx))
            resource.setSharedId(rsrcCtx)
            self.addNodeAndPreEdge(resource)
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(resource)

        endTry = CFNode(CFNodeKind.TRY_END)
        endTry.setLineOfCode(0)
        endTry.setFile(self.filePath)
        endTry.setCode("end-try")
        self.currentCFG.addVertex(endTry)

        self.tryBlocks.push(Block(tryNode, endTry))
        self.visit(ctx.block())
        self.popAddPreEdgeTo(endTry)

        # If there is a finally-block, visit it first
        finallyNode = None
        endFinally = None
        if ctx.finallyBlock() is not None:
            finallyNode = CFNode(CFNodeKind.FINALLY)
            finallyNode.setLineOfCode(ctx.finallyBlock().start.line)
            finallyNode.setFile(self.filePath)
            finallyNode.setCode("finally")
            finallyNode.setSharedId(ctx.finallyBlock())
            self.currentCFG.addVertex(finallyNode)
            self.currentCFG.addEdge(CFEdge(endTry, CFEdgeKind.EPS, finallyNode))

            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(finallyNode)
            self.visit(ctx.finallyBlock().block())

            endFinally = CFNode(CFNodeKind.FINALLY_END)
            endFinally.setLineOfCode(0)
            endFinally.setFile(self.filePath)
            endFinally.setCode("end-finally")
            self.addNodeAndPreEdge(endFinally)

        # Now visit any available catch clauses
        if ctx.catchClause() is not None:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            endCatch = CFNode(CFNodeKind.CATCH_END)
            endCatch.setLineOfCode(0)
            endCatch.setFile(self.filePath)
            endCatch.setCode("end-catch")
            self.currentCFG.addVertex(endCatch)

            for cx in ctx.catchClause():
                # connect the try-node to all catch-nodes;
                # create a single end-catch for all catch-blocks;
                catchNode = CFNode(CFNodeKind.CATCH)
                catchNode.setLineOfCode(cx.start.line)
                catchNode.setFile(self.filePath)
                catchNode.setCode("catch (" + cx.catchType().getText() + " " + cx.IDENTIFIER().getText() + ")")
                catchNode.setSharedId(cx)
                self.currentCFG.addVertex(catchNode)
                self.currentCFG.addEdge(CFEdge(endTry, CFEdgeKind.THROWS, catchNode))

                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(catchNode)
                self.visit(cx.block())
                self.popAddPreEdgeTo(endCatch)

            if finallyNode is not None:
                # connect end-catch node to finally-node,
                # and push end-finally to the stack ...
                self.currentCFG.addEdge(CFEdge(endCatch, CFEdgeKind.EPS, finallyNode))
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(endFinally)
            else:
                # connect end-catch node to end-try,
                # and push end-try to the the stack ...
                self.currentCFG.addEdge(CFEdge(endCatch, CFEdgeKind.EPS, endTry))
                self.preEdgeKinds.push(CFEdgeKind.EPS)
                self.preNodes.push(endTry)
        else:
            # No catch-clause; it's a try-finally
            # push end-finally to the stack ...
            self.preEdgeKinds.push(CFEdgeKind.EPS)
            self.preNodes.push(endFinally)

        return None

    def visitStmtThrow(self, ctx:JavaParser.StmtThrowContext):
        # statement: THROW expression ';'
        throwNode = CFNode(CFNodeKind.THROW)
        throwNode.setLineOfCode(ctx.start.line)
        throwNode.setFile(self.filePath)
        throwNode.setCode("throw " + getOriginalCodeText(ctx.expression()))
        throwNode.setSharedId(ctx)
        self.addNodeAndPreEdge(throwNode)

        if not self.tryBlocks.isEmpty():
            tryBlock = self.tryBlocks.peek()
            self.currentCFG.addEdge(CFEdge(throwNode, CFEdgeKind.THROWS, tryBlock.end))
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

        expr = CFNode(CFNodeKind.EXPR)
        expr.setLineOfCode(ctx.start.line)
        expr.setFile(self.filePath)
        expr.setCode(getOriginalCodeText(ctx))
        expr.setSharedId(ctx)
        self.addNodeAndPreEdge(expr)
        self.preEdgeKinds.push(CFEdgeKind.EPS)
        self.preNodes.push(expr)
        return None

    def addNodeAndPreEdge(self, node: CFNode) -> None:
        # Добавляет узел в CFG и пристыковывает к нему ребро
        self.currentCFG.addVertex(node)
        self.popAddPreEdgeTo(node)

    def popAddPreEdgeTo(self, node: CFNode) -> None:
        # Создает ребро между предыдущим узлом и узлом 'node'.
        # Тип ребра извлекается из очереди 'preEdgeKinds'
        if self.dontPop:
            self.dontPop = False
        else:
            src = self.preNodes.pop()
            edgeKind = self.preEdgeKinds.pop()
            edge = CFEdge(src, edgeKind, node)
            self.currentCFG.addEdge(edge)

        for i in range(self.casesQueue.size(), 0, -1):
            self.currentCFG.addEdge(CFEdge(self.casesQueue.pop(), CFEdgeKind.TRUE, node))
