import logging
import os
from typing import List, Dict

from GremlinDriver import Gremlin
from gremlin_python.process.graph_traversal import __
from TypeDeterminator import TypeDeterminator
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from db import Database
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.ddg.DFNode import DFNode
from graphs.ddg.DataFlowGraph import DataFlowGraph
from graphs.digraph import Edge
from utils import isUsableExpression, getOriginalCodeText, Queue, getIdByCtx, doesMethodStateDef, \
    getDataFlowParent, Stack
from JavaStructures import JavaField, MethodDefInfo, JavaClass, JavaMethod

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False


class DFGVisitor(JavaParserVisitor):
    def __init__(self, iteration, ddgs: List[DataFlowGraph],
                 ast: AbstractSyntaxTree, filePath: str, db: Database, projectConfig):
        self.analysisVisit = False
        self.iteration = iteration
        self.ddgs = ddgs
        self.localVars = []
        self.useList = set()
        self.defList = set()
        self.selfFlowList = set()
        self.changed = False
        self.methodParams = []
        self.activeClasses = Stack()
        self.ast = ast
        self.filePath = filePath
        self.db = db
        self.projectConfig = projectConfig

        self.currentDFG = None
        self.currentMethod = None
        self.packageName = None

    def analyseDefUse(self, node, expression):
        logger.debug("--- ANALYSIS ---")
        logger.debug(node)
        self.analysisVisit = True
        expr = self.visit(expression)
        logger.debug(expr)

        localVarStr = ""
        localVarStr += "LOCAL VARS = ["
        for lv in self.localVars:
            localVarStr += lv.type + " " + lv.name + ", "
        localVarStr += "]"
        logger.debug(localVarStr)

        if isUsableExpression(expr):
            self.useList.add(expr)
            logger.debug("USABLE")

        self.analysisVisit = False
        logger.debug("Changed = " + str(self.changed))
        logger.debug("DEFs = " + ' '.join(node.getAllDEFs()))
        logger.debug("USEs = " + ' '.join(node.getAllUSEs()))

        for DEF in self.defList:
            status = self.isDefined(DEF)
            if status > -1:
                self.changed |= node.addDEF(DEF)
            else:
                logger.debug(f"{DEF} is not defined!")
        logger.debug("Changed = " + str(self.changed))
        logger.debug("DEFs = " + ' '.join(node.getAllDEFs()))

        for USE in self.useList:
            status = self.isDefined(USE)
            if status > -1:
                self.changed |= node.addUSE(USE)
            else:
                logger.debug(f"{USE} is not defined!")
        logger.debug("Changed = " + str(self.changed))
        logger.debug("USEs = " + ' '.join(node.getAllUSEs()))

        for selfFlow in self.selfFlowList:
            status = self.isDefined(selfFlow)
            if status > -1:
                self.changed |= node.addSelfFlow(selfFlow)
            else:
                logger.debug(f"{selfFlow} is not defined!")
        logger.debug("Changed = " + str(self.changed))
        logger.debug("SelfFlows = " + ' '.join(node.getAllSelfFlows()))

        self.defList.clear()
        self.useList.clear()
        self.selfFlowList.clear()
        logger.debug("----------------")

    def isDefined(self, _id: str):
        for i in range(0, len(self.methodParams)):
            if self.methodParams[i].name == _id:
                return i

        for local in self.localVars:
            if local.name == _id:
                return 202

        if _id.startswith("this."):
            _id = _id[:5]

        # for field in self.activeClasses.peek().getAllFields():
        #     if field.NAME == _id:
        #         return 101

        for cls in self.activeClasses.items:
            for field in cls.getAllFields():
                if field.name == _id:
                    return 303

        return -1

    # def findDefInfo(self, name: str, type: str, params: List[JavaField]) -> MethodDefInfo:
    #     infoList = self.methodDEFs.get(name)
    #     if len(infoList) > 1:
    #         for info in infoList:
    #             if not info.PACKAGE.equals(self.activeClasses.peek().PACKAGE):
    #                 continue
    #             if not info.CLASS_NAME.equals(self.activeClasses.peek().NAME):
    #                 continue
    #             if (info.RET_TYPE is None and type is not None) or \
    #                     (info.RET_TYPE is not None and type is None):
    #                 continue
    #             if type is not None and not type.startswith(info.RET_TYPE):
    #                 continue
    #
    #             if info.PARAM_TYPES is not None:
    #                 if len(info.PARAM_TYPES) != len(params):
    #                     continue
    #
    #                 for i in range(len(params)):
    #                     # TODO fix a loop
    #                     if (!params[i].TYPE.startsWith(info.PARAM_TYPES[i]))
    #                         continue
    #             elif len(params) > 0:
    #                 continue
    #             return info
    #     else:
    #         if len(infoList) == 1:
    #             return infoList[0]
    #     return None

    # ****************************************
    # ************* DECLARATIONS *************
    # ****************************************

    def visitPackageDeclaration(self, ctx:JavaParser.PackageDeclarationContext):
        # packageDeclaration: annotation* PACKAGE qualifiedName ';'
        self.packageName = ctx.qualifiedName().getText()
        return None

    def visitClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        # CLASS IDENTIFIER typeParameters? (EXTENDS typeType)? (IMPLEMENTS typeList)? classBody
        className = ctx.IDENTIFIER().getText()
        qualifiedName = f"{self.packageName}.{className}"
        cls = self.db.getJavaClass(qualifiedName)
        if cls is not None:
            self.activeClasses.push(cls)
            self.visit(ctx.classBody())
            self.activeClasses.pop()

        return None

    def visitEnumDeclaration(self, ctx: JavaParser.EnumDeclarationContext):
        # ENUM IDENTIFIER (IMPLEMENTS typeList)? '{' enumConstants? ','? enumBodyDeclarations? '}'
        # Just ignore enums for now ...
        pass

    def visitInterfaceDeclaration(self, ctx: JavaParser.InterfaceDeclarationContext):
        # INTERFACE IDENTIFIER typeParameters? (EXTENDS typeList)? interfaceBody
        # Just ignore enums for now ...
        pass

    def visitClassBodyDeclaration(self, ctx: JavaParser.ClassBodyDeclarationContext):
        # ';' | STATIC? block | modifier* memberDeclaration
        if ctx.block() is not None:
            self.localVars.clear()
            self.methodDefInfo = MethodDefInfo(None, "static-block", "", self.activeClasses.peek().name, None)
            return None
        else:
            return self.visitChildren(ctx)

    def visitConstructorDeclaration(self, ctx: JavaParser.ConstructorDeclarationContext):
        # IDENTIFIER formalParameters (THROWS qualifiedNameList)? constructorBody=block
        if self.iteration == 1:
            entry = DFNode()
            entry.setLineOfCode(ctx.start.line)
            entry.setFile(self.filePath)
            args = getOriginalCodeText(ctx.formalParameters())
            entry.setCode(ctx.IDENTIFIER().getText() + args)
            entry.setOptionalProperty("name", ctx.IDENTIFIER().getText())
            entry.setSharedId(ctx)
            self.currentDFG = DataFlowGraph()
            self.currentMethod = ctx.IDENTIFIER().getText()
            self.currentDFG.setProperty("className", self.activeClasses.peek().name)
            self.currentDFG.setProperty("methodName", self.currentMethod)
            self.currentDFG.addVertex(entry)

            # Extract all parameters and IDs
            paramIDs = []
            paramTypes = []
            if ctx.formalParameters().formalParameterList() is not None:
                for prm in ctx.formalParameters().formalParameterList().formalParameter():
                    paramTypes.append(self.visitTypeType(prm.typeType()))
                    paramIDs.append(prm.variableDeclaratorId().IDENTIFIER().getText())
                lastParam = ctx.formalParameters().formalParameterList().lastFormalParameter()
                if lastParam is not None:
                    paramTypes.append(self.visitTypeType(lastParam.typeType()))
                    paramIDs.append(lastParam.variableDeclaratorId().IDENTIFIER().getText())
            self.methodParams = []
            for i in range(len(paramTypes)):
                self.methodParams.append(JavaField(
                    None, False, paramTypes[i], paramIDs[i]
                ))
            # entry.setProperty("params", self.methodParams)

            # Adding DEFs for input parameters
            for pid in paramIDs:
                self.changed |= entry.addDEF(pid)
        else:
            self.currentMethod = ctx.IDENTIFIER().getText()
            qualifiedName = f"{self.packageName}.{self.activeClasses.peek().name}.{self.currentMethod}"
            self.currentDFG = self.getDFG(qualifiedName)
            entry = self.currentDFG.getNodeByCtx(ctx)

        self.localVars.clear()
        if ctx.constructorBody is not None:
            self.visit(ctx.constructorBody)
            qualifiedName = f"{self.packageName}.{self.activeClasses.peek().name}.{self.currentMethod}"
            self.ddgs[qualifiedName] = self.currentDFG
            self.currentDFG = None
            self.currentMethod = None

        self.localVars.clear()
        return None

    def visitMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        # methodDeclaration: typeTypeOrVoid IDENTIFIER formalParameters ('[' ']')* (THROWS qualifiedNameList)? methodBody
        # formalParameters: '(' formalParameterList? ')'
        # formalParameterList: formalParameter (',' formalParameter)* (',' lastFormalParameter)? | lastFormalParameter
        # formalParameter: variableModifier* typeType variableDeclaratorId
        # lastFormalParameter: variableModifier* typeType '...' variableDeclaratorId
        if self.iteration == 1:
            entry = DFNode()
            entry.setLineOfCode(ctx.start.line)
            entry.setFile(self.filePath)
            retType = ctx.typeTypeOrVoid().getText()
            args = getOriginalCodeText(ctx.formalParameters())
            entry.setCode(retType + " " + ctx.IDENTIFIER().getText() + args)
            entry.setOptionalProperty("name", ctx.IDENTIFIER().getText())
            entry.setOptionalProperty("type", retType)
            entry.setSharedId(ctx)
            self.currentDFG = DataFlowGraph()
            self.currentMethod = ctx.IDENTIFIER().getText()
            self.currentDFG.setProperty("className", self.activeClasses.peek().name)
            self.currentDFG.setProperty("methodName", self.currentMethod)
            self.currentDFG.addVertex(entry)

            # Extract all parameters and IDs
            paramIDs = []
            paramTypes = []
            if ctx.formalParameters().formalParameterList() is not None:
                for prm in ctx.formalParameters().formalParameterList().formalParameter():
                    paramTypes.append(self.visitTypeType(prm.typeType()))
                    paramIDs.append(prm.variableDeclaratorId().IDENTIFIER().getText())
                lastParam = ctx.formalParameters().formalParameterList().lastFormalParameter()
                if lastParam is not None:
                    paramTypes.append(self.visitTypeType(lastParam.typeType()))
                    paramIDs.append(lastParam.variableDeclaratorId().IDENTIFIER().getText())
            self.methodParams = []
            for i in range(len(paramTypes)):
                self.methodParams.append(JavaField(
                    None, False, paramTypes[i], paramIDs[i]
                ))
            # entry.setProperty("params", self.methodParams)

            # Adding DEFs for input parameters
            for pid in paramIDs:
                self.changed |= entry.addDEF(pid)
        else:
            self.currentMethod = ctx.IDENTIFIER().getText()
            qualifiedName = f"{self.packageName}.{self.activeClasses.peek().name}.{self.currentMethod}"
            self.currentDFG = self.getDFG(qualifiedName)
            entry = self.currentDFG.getNodeByCtx(ctx)

        self.localVars.clear()
        if ctx.methodBody() is not None:
            self.visit(ctx.methodBody())
            qualifiedName = f"{self.packageName}.{self.activeClasses.peek().name}.{self.currentMethod}"
            self.ddgs[qualifiedName] = self.currentDFG
            self.currentDFG = None
            self.currentMethod = None

        self.localVars.clear()
        return None

    def visitTypeType(self, ctx: JavaParser.TypeTypeContext):
        # typeType: annotation? (classOrInterfaceType | primitiveType) ('[' ']')*
        # classOrInterfaceType: IDENTIFIER typeArguments? ('.' IDENTIFIER typeArguments?)*
        return ctx.getText()

    def visitLocalVariableDeclaration(self, ctx: JavaParser.LocalVariableDeclarationContext):
        # localVariableDeclaration : variableModifier* typeType variableDeclarators
        # variableDeclarators : variableDeclarator (',' variableDeclarator)*
        # variableDeclarator : variableDeclaratorId ('=' variableInitializer)?

        # if self.analysisVisit:
        #     return self.visit(ctx.variableDeclarators())

        for var in ctx.variableDeclarators().variableDeclarator():
            self.localVars.append(JavaField(
                None,
                False,
                self.visit(ctx.typeType()),
                var.variableDeclaratorId().IDENTIFIER().getText()
            ))

            if self.analysisVisit:
                return self.visit(ctx.variableDeclarators())

            if self.iteration == 1:
                declr = DFNode()
                declr.setLineOfCode(var.start.line)
                declr.setFile(self.filePath)
                declr.setCode(getOriginalCodeText(var))
                declr.setSharedId(var)
                self.currentDFG.addVertex(declr)
            else:
                declr = self.currentDFG.getNodeByCtx(var)

            self.analyseDefUse(declr, var)
        return None

    # ************************************************************
    # ************    STATEMENTS *********************************
    # ************************************************************

    def visitBlock(self, ctx: JavaParser.BlockContext):
        # block: '{' blockStatement* '}'
        # Local vars defined inside a block, are only valid till the end of that block.
        entrySize = len(self.localVars)
        self.visitChildren(ctx)
        if len(self.localVars) > entrySize:
            del self.localVars[entrySize:]
        return None

    def visitStmtExpr(self, ctx: JavaParser.StmtExprContext):
        # expression ';'
        if self.analysisVisit:
            return self.visit(ctx.expression())

        if self.iteration == 1:
            expr = DFNode()
            expr.setLineOfCode(ctx.start.line)
            expr.setFile(self.filePath)
            expr.setCode(getOriginalCodeText(ctx))
            expr.setSharedId(ctx)
            self.currentDFG.addVertex(expr)
        else:
            expr = self.currentDFG.getNodeByCtx(ctx)

        self.analyseDefUse(expr, ctx.expression())
        return None

    def visitStmtIf(self, ctx: JavaParser.StmtIfContext):
        # IF parExpression trueClause=statement (ELSE falseClause=statement)?
        if self.iteration == 1:
            ifNode = DFNode()
            ifNode.setLineOfCode(ctx.start.line)
            ifNode.setFile(self.filePath)
            ifNode.setCode("if " + getOriginalCodeText(ctx.parExpression()))
            ifNode.setSharedId(ctx)
            self.currentDFG.addVertex(ifNode)
        else:
            ifNode = self.currentDFG.getNodeByCtx(ctx)

        self.analyseDefUse(ifNode, ctx.parExpression().expression())
        self.visit(ctx.trueClause)

        if ctx.falseClause is not None:
            self.visit(ctx.falseClause)

        return None

    def visitStmtFor(self, ctx: JavaParser.StmtForContext):
        # FOR '(' forControl ')' statement
        entrySize = len(self.localVars)
        # First, we should check type of for-loop ...
        if ctx.forControl().enhancedForControl() is not None:
            # enhancedForControl: variableModifier* typeType variableDeclaratorId ':' expression
            if self.iteration == 1:
                forExpr = DFNode()
                forExpr.setLineOfCode(ctx.forControl().start.line)
                forExpr.setFile(self.filePath)
                forExpr.setCode("for (" + getOriginalCodeText(ctx.forControl()) + ")")
                forExpr.setSharedId(ctx.forControl().enhancedForControl())
                self.currentDFG.addVertex(forExpr)
            else:
                forExpr = self.currentDFG.getNodeByCtx(ctx.forControl().enhancedForControl())

            # Now analyse DEF-USE by visiting the expression ...
            type = self.visitTypeType(ctx.forControl().enhancedForControl().typeType())
            var = ctx.forControl().enhancedForControl().variableDeclaratorId().IDENTIFIER().getText()
            self.localVars.append(JavaField(None, False, type, var))
            self.changed |= forExpr.addDEF(var)
            self.analyseDefUse(forExpr, ctx.forControl().enhancedForControl().expression())
        else:
            # forInit? ';' expression? ';' forUpdate=expressionList?
            if ctx.forControl().forInit() is not None:
                if self.iteration == 1:
                    forInit = DFNode()
                    forInit.setLineOfCode(ctx.forControl().forInit().start.line)
                    forInit.setFile(self.filePath)
                    forInit.setCode(getOriginalCodeText(ctx.forControl().forInit()))
                    forInit.setSharedId(ctx.forControl().forInit())
                    self.currentDFG.addVertex(forInit)
                else:
                    forInit = self.currentDFG.getNodeByCtx(ctx.forControl().forInit())
                # Now analyse DEF-USE by visiting the expression ...
                if ctx.forControl().forInit().expressionList() is not None:
                    self.analyseDefUse(forInit, ctx.forControl().forInit().expressionList())
                else:
                    self.analyseDefUse(forInit, ctx.forControl().forInit().localVariableDeclaration())
            if ctx.forControl().expression() is not None:
                if self.iteration == 1:
                    forExpr = DFNode()
                    forExpr.setLineOfCode(ctx.forControl().expression().start.line)
                    forExpr.setFile(self.filePath)
                    forExpr.setCode("for (" + getOriginalCodeText(ctx.forControl().expression()) + ")")
                    forExpr.setSharedId(ctx.forControl().expression())
                    self.currentDFG.addVertex(forExpr)
                else:
                    forExpr = self.currentDFG.getNodeByCtx(ctx.forControl().expression())
                # Now analyse DEF-USE by visiting the expression ...
                self.analyseDefUse(forExpr, ctx.forControl().expression())
            if ctx.forControl().forUpdate is not None:
                if self.iteration == 1:
                    forUpdate = DFNode()
                    forUpdate.setLineOfCode(ctx.forControl().forUpdate.start.line)
                    forUpdate.setFile(self.filePath)
                    forUpdate.setCode(getOriginalCodeText(ctx.forControl().forUpdate))
                    forUpdate.setSharedId(ctx.forControl().forUpdate)
                    self.currentDFG.addVertex(forUpdate)
                else:
                    forUpdate = self.currentDFG.getNodeByCtx(ctx.forControl().forUpdate)

                # Now analyse DEF-USE by visiting the expression ...
                self.analyseDefUse(forUpdate, ctx.forControl().forUpdate)

        # visit loop body
        visit = self.visit(ctx.statement())
        # clear any local vars defined in the for loop
        if len(self.localVars) > entrySize:
            del self.localVars[entrySize:]
        return visit

    def visitStmtWhile(self, ctx: JavaParser.StmtWhileContext):
        # WHILE parExpression statement
        if self.iteration == 1:
            whileNode = DFNode()
            whileNode.setLineOfCode(ctx.start.line)
            whileNode.setFile(self.filePath)
            whileNode.setCode("while " + getOriginalCodeText(ctx.parExpression()))
            whileNode.setSharedId(ctx)
            self.currentDFG.addVertex(whileNode)
        else:
            whileNode = self.currentDFG.getNodeByCtx(ctx)

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(whileNode, ctx.parExpression().expression())
        return self.visit(ctx.statement())

    def visitStmtDoWhile(self, ctx: JavaParser.StmtDoWhileContext):
        # DO statement WHILE parExpression ';'
        self.visit(ctx.statement())
        if self.iteration == 1:
            whileNode = DFNode()
            whileNode.setLineOfCode(ctx.start.line)
            whileNode.setFile(self.filePath)
            whileNode.setCode("while " + getOriginalCodeText(ctx.parExpression()))
            whileNode.setSharedId(ctx)
            self.currentDFG.addVertex(whileNode)
        else:
            whileNode = self.currentDFG.getNodeByCtx(ctx)

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(whileNode, ctx.parExpression().expression())
        return None

    def visitStmtSwitch(self, ctx: JavaParser.StmtSwitchContext):
        # SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'
        # switchBlockStatementGroup : switchLabel+ blockStatement+
        if self.iteration == 1:
            switchNode = DFNode()
            switchNode.setLineOfCode(ctx.start.line)
            switchNode.setFile(self.filePath)
            switchNode.setCode("switch " + getOriginalCodeText(ctx.parExpression()))
            switchNode.setSharedId(ctx)
            self.currentDFG.addVertex(switchNode)
        else:
            switchNode = self.currentDFG.getNodeByCtx(ctx)

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(switchNode, ctx.parExpression().expression())

        for scx in ctx.switchBlockStatementGroup():
            self.visit(scx)
        for scx in ctx.switchLabel():
            self.visit(scx)
        return None

    def visitStmtReturn(self, ctx: JavaParser.StmtReturnContext):
        # RETURN expression? ';'
        if self.iteration == 1:
            ret = DFNode()
            ret.setLineOfCode(ctx.start.line)
            ret.setFile(self.filePath)
            ret.setCode(getOriginalCodeText(ctx))
            ret.setSharedId(ctx)
            self.currentDFG.addVertex(ret)
        else:
            ret = self.currentDFG.getNodeByCtx(ctx)
        # Now analyse DEF-USE by visiting the expression ...
        if ctx.expression() is not None:
            self.analyseDefUse(ret, ctx.expression())
        return None

    def visitStmtSynchronized(self, ctx: JavaParser.StmtSynchronizedContext):
        # SYNCHRONIZED parExpression block
        if self.iteration == 1:
            syncStmt = DFNode()
            syncStmt.setLineOfCode(ctx.start.line)
            syncStmt.setFile(self.filePath)
            syncStmt.setCode("synchronized " + getOriginalCodeText(ctx.parExpression()))
            syncStmt.setSharedId(ctx)
            self.currentDFG.addVertex(syncStmt)
        else:
            syncStmt = self.currentDFG.getNodeByCtx(ctx)

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(syncStmt, ctx.parExpression().expression())

        return self.visit(ctx.block())

    def visitStmtThrow(self, ctx: JavaParser.StmtThrowContext):
        # THROW expression ';'
        if self.iteration == 1:
            throwNode = DFNode()
            throwNode.setLineOfCode(ctx.start.line)
            throwNode.setFile(self.filePath)
            throwNode.setCode("throw " + getOriginalCodeText(ctx.expression()))
            throwNode.setSharedId(ctx)
            self.currentDFG.addVertex(throwNode)
        else:
            throwNode = self.currentDFG.getNodeByCtx(ctx)

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(throwNode, ctx.expression())
        return None

    def visitStmtTry(self, ctx: JavaParser.StmtTryContext):
        # TRY block (catchClause+ finallyBlock? | finallyBlock)

        # The 'try' block has no DEF-USE effect, so no need for DFNodes;
        # just visit the 'block'
        self.visit(ctx.block())

        # But the 'catchClause' define a local exception variable;
        # so we need to visit any available catch clauses
        if ctx.catchClause() is not None and len(ctx.catchClause()) > 0:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            for cx in ctx.catchClause():
                if self.iteration == 1:
                    catchNode = DFNode()
                    catchNode.setLineOfCode(cx.start.line)
                    catchNode.setFile(self.filePath)
                    catchNode.setCode("catch (" + cx.catchType().getText() + cx.IDENTIFIER().getText() + ")")
                    catchNode.setSharedId(cx)
                    self.currentDFG.addVertex(catchNode)
                else:
                    catchNode = self.currentDFG.getNodeByCtx(cx)

                # Define the exception var
                type = cx.catchType().getText()
                var = cx.IDENTIFIER().getText()
                exceptionVar = JavaField(None, False, type, var)
                self.localVars.append(exceptionVar)
                self.changed |= catchNode.addDEF(var)

                self.visit(cx.block())
                self.localVars.remove(exceptionVar)

        if ctx.finallyBlock() is not None:
            # finallyBlock: FINALLY block
            self.visit(ctx.finallyBlock().block())

        return None

    def visitStmtTryResource(self, ctx: JavaParser.StmtTryResourceContext):
        # TRY resourceSpecification block catchClause* finallyBlock?
        # resourceSpecification: '(' resources ';'? ')'
        # resources: resource (';' resource)*
        # resource: variableModifier* classOrInterfaceType variableDeclaratorId '=' expression

        entrySize = len(self.localVars)

        # Analyze all resources
        for rsrx in ctx.resourceSpecification().resources().resource():
            if self.iteration == 1:
                resource = DFNode()
                resource.setLineOfCode(rsrx.start.line)
                resource.setFile(self.filePath)
                resource.setCode(getOriginalCodeText(rsrx))
                resource.setSharedId(rsrx)
                self.currentDFG.addVertex(resource)
            else:
                resource = self.currentDFG.getNodeByCtx(rsrx)

            # Define the resource variable
            type = rsrx.classOrInterfaceType().getText()
            var = rsrx.variableDeclaratorId().getText()
            self.localVars.append(JavaField(None, False, type, var))

            # Now analyse DEF-USE by visiting the expression ...
            self.analyseDefUse(resource, rsrx)

        # The 'try' block has no DEF-USE effect, so no need for DFNodes;
        # just visit the 'block'
        self.visit(ctx.block())

        # But the 'catchClause' define a local exception variable;
        # so we need to visit any available catch clauses
        if ctx.catchClause() is not None and len(ctx.catchClause()) > 0:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            for cx in ctx.catchClause():
                if self.iteration == 1:
                    catchNode = DFNode()
                    catchNode.setLineOfCode(cx.start.line)
                    catchNode.setFile(self.filePath)
                    catchNode.setCode("catch (" + cx.catchType().getText() + cx.IDENTIFIER().getText() + ")")
                    catchNode.setSharedId(cx)
                    self.currentDFG.addVertex(catchNode)
                else:
                    catchNode = self.currentDFG.getNodeByCtx(cx)

                # Define the exception var
                type = cx.catchType().getText()
                var = cx.IDENTIFIER().getText()
                exceptionVar = JavaField(None, False, type, var)
                self.localVars.append(exceptionVar)
                self.changed |= catchNode.addDEF(var)

                self.visit(cx.block())
                self.localVars.remove(exceptionVar)

        if ctx.finallyBlock() is not None:
            # finallyBlock: FINALLY block
            self.visit(ctx.finallyBlock().block())

        # Remove resources from local vars ...
        if len(self.localVars) > entrySize:
            del self.localVars[entrySize:]

        return None

    # *******************************************************
    # *** NON-DETERMINANT EXPRESSIONS                   *****
    # *******************************************************

    def visitExprPrimary(self, ctx: JavaParser.ExprPrimaryContext):
        # expression: primary # ExprPrimary
        # primary
        #     : '(' expression ')'
        #     | THIS
        #     | SUPER
        #     | literal
        #     | IDENTIFIER
        #     | typeTypeOrVoid '.' CLASS
        #     | nonWildcardTypeArguments (explicitGenericInvocationSuffix | THIS arguments)
        #     ;
        #
        # literal
        #     : integerLiteral
        #     | floatLiteral
        #     | CHAR_LITERAL
        #     | STRING_LITERAL
        #     | BOOL_LITERAL
        #     | NULL_LITERAL
        #
        # nonWildcardTypeArguments
        #     : '<' typeList '>'
        #
        # explicitGenericInvocationSuffix
        #     : SUPER superSuffix
        #     | IDENTIFIER arguments

        primary = ctx.primary()
        if primary.getText().startswith("(") and primary.getText().endswith(")"):
            return "(" + self.visit(primary.expression())
        if primary.getText() == "this":
            return "this"
        if primary.getText() == "super":
            return "super"
        if primary.literal() is not None:
            if primary.literal().integerLiteral() is not None:
                return "$INT"
            if primary.literal().floatLiteral() is not None:
                return "$DBL"
            if primary.literal().CHAR_LITERAL() is not None:
                return "$CHR"
            if primary.literal().STRING_LITERAL() is not None:
                return "$STR"
            if primary.literal().BOOL_LITERAL() is not None:
                return "$BOOL"
            return "$NULL"
        if primary.IDENTIFIER() is not None:
            return primary.IDENTIFIER().getText()
        if primary.getText().endswith(".class"):
            return "$CLS"
        return primary.getText()

    def visitExprDot(self, ctx: JavaParser.ExprDotContext):
        # expression: expression bop='.'
        #       ( IDENTIFIER
        #       | methodCall
        #       | THIS
        #       | NEW nonWildcardTypeArguments? innerCreator
        #       | SUPER superSuffix
        #       | explicitGenericInvocation
        #       )                                   # ExprDot

        if ctx.IDENTIFIER() is not None:
            return self.visit(ctx.expression()) + "." + ctx.IDENTIFIER().getText()

        if ctx.methodCall() is not None:
            # methodCall
            #     : IDENTIFIER '(' expressionList? ')'
            #     | THIS '(' expressionList? ')'
            #     | SUPER '(' expressionList? ')'
            # methodCallCtx = ctx.methodCall()
            # if methodCallCtx.expressionList() is not None:
            #     expressionListStr = self.visit(methodCallCtx.expressionList())
            # else:
            #     expressionListStr = ""
            #
            # expression = self.visit(ctx.expression())
            # if isUsableExpression(expression):
            #     self.useList.add(expression)
            #
            # return self.visit(ctx.expression()) + "." \
            #        + methodCallCtx.getChild(0).getText() + "(" + expressionListStr + ")"
            return self.visit(ctx.expression()) + "." + self.visit(ctx.methodCall())

        if ctx.THIS() is not None:
            return self.visit(ctx.expression()) + ".this"

        if ctx.NEW() is not None:
            # expression bop='.' NEW nonWildcardTypeArguments? innerCreator
            # innerCreator: IDENTIFIER nonWildcardTypeArgumentsOrDiamond? classCreatorRest
            # classCreatorRest: arguments classBody?

            # 1st process 'expression'
            expression = self.visit(ctx.expression())
            if isUsableExpression(expression):
                self.useList.add(expression)
            # 2nd process 'innerCreator'
            creator = ctx.innerCreator().IDENTIFER().getText()
            # 3d process constructor arguments ...
            argsCtx = ctx.innerCreator().classCreatorRest().arguments()
            rest = self.visitMethodArgs(argsCtx)
            return expression + ".$NEW " + creator + rest

        if ctx.SUPER() is not None:
            # expression bop='.' SUPER superSuffix
            # superSuffix
            #     : arguments
            #     | '.' IDENTIFIER arguments?

            result = ""
            expr = self.visit(ctx.expression())
            if isUsableExpression(expr):
                self.useList.add(expr)
            result += expr + ".super"

            if ctx.superSuffix().arguments() is not None:
                self.useList.add(result)
                if ctx.superSuffix().getText().startswith("."):
                    # expr.super.method(...) call
                    result += "." + ctx.superSuffix().IDENTIFIER().getText() + "("
                # else expr.super(...) constructor call
                result += self.visitMethodArgs(ctx.superSuffix().arguments().expressionList())
                result += ")"

            return result

        if ctx.explicitGenericInvocation() is not None:
            # expression bop='.' explicitGenericInvocation
            # explicitGenericInvocation
            #     : nonWildcardTypeArguments explicitGenericInvocationSuffix
            # nonWildcardTypeArguments
            #     : '<' typeList '>'
            # explicitGenericInvocationSuffix
            #     : SUPER superSuffix
            #     | IDENTIFIER arguments

            expression = self.visit(ctx.expression())
            if isUsableExpression(expression):
                self.useList.add(expression)
            suffixContext = ctx.explicitGenericInvocation().explicitGenericInvocationSuffix()
            if suffixContext.IDENTIFIER() is not None:
                invocSuffix = suffixContext.IDENTIFIER().getText()
                invocSuffix += '(' + self.visitMethodArgs(suffixContext.arguments().expressionList()) + ')'
            else:
                invocSuffix = "super"
                if suffixContext.superSuffix().Identifier() is not None:
                    invocSuffix += '.' + suffixContext.superSuffix().IDENTIFIER().getText()
                if suffixContext.superSuffix().arguments() is not None:
                    invocSuffix += '(' + self.visitMethodArgs(suffixContext.superSuffix().arguments().expressionList()
                                                              ) + ')'
            return expression + '.' + ctx.explicitGenericInvocation().nonWildcardTypeArguments().getText() + invocSuffix

        return self.visit(ctx.expression()) + ".UNKNOWN"

    def visitExprCasting(self, ctx: JavaParser.ExprCastingContext):
        # expression: '(' typeType ')' expression

        return "$CAST(" + self.visit(ctx.typeType()) + ")" + self.visit(ctx.expression())

    def visitExpressionList(self, ctx: JavaParser.ExpressionListContext):
        # expressionList: expression (',' expression)*
        expr = self.visit(ctx.expression(0))
        if isUsableExpression(expr):
            self.useList.add(expr)
        expList = expr
        for i in range(1, len(ctx.expression())):
            expr = self.visit(ctx.expression(i))
            if isUsableExpression(expr):
                self.useList.add(expr)
            expList += ", " + expr
        return expList

    # *************************************************************
    # *** DETERMINANT EXPRESSIONS (RETURN OBJECT) ***
    # *************************************************************

    # Visit the list of arguments of a method call, and return a proper string.
    # This method will also add usable expressions to the USE-list.
    def visitMethodArgs(self, ctx: JavaParser.ExpressionListContext, methodName: str = None, callNode: DFNode = None):
        # expressionList: expression (',' expression)*
        if ctx is not None:
            args = ""
            argList = ctx.expression()
            arg = self.visit(argList[0])
            if isUsableExpression(arg):
                self.useList.add(arg)
                # if defInfo is not None and defInfo.argDEFs[0]:
                #     self.defList.add(arg)

                # if methodName is not None:
                #     callNode.IP_DEFs = {
                #         "methodName": methodName,
                #         "edges": [arg + "-"]
                #     }

            if methodName is not None:
                if "." in methodName:
                    if self.db.getCFG(methodName):
                        entrySharedId = self.db.getCFG(methodName).nodes[0].getSharedId()
                        callNode.IP_DEFs = {
                            "entrySharedId": entrySharedId
                        }
                else:
                    methodQN = self.packageName + "." + self.activeClasses.peek().name + "." + methodName
                    if self.db.getCFG(methodQN):
                        entrySharedId = self.db.getCFG(methodQN).nodes[0].getSharedId()
                        callNode.IP_DEFs = {
                            "entrySharedId": entrySharedId
                        }

            for i in range(1, len(argList)):
                arg = self.visit(argList[i])
                args += ", " + arg
                if isUsableExpression(arg):
                    self.useList.add(arg)
                    # if defInfo is not None and defInfo.argDEFs()[i]:
                    #     self.defList.add(arg)
                    # if methodName is not None and callNode.IP_DEFs is not None:
                    #     callNode.IP_DEFs["edges"].append(arg + "-")
            return args
        else:
            return ""

    def visitMethodCall(self, ctx: JavaParser.MethodCallContext):
        # methodCall
        #     : IDENTIFIER '(' expressionList? ')'
        #     | THIS '(' expressionList? ')'
        #     | SUPER '(' expressionList? ')'

        callee = None
        calleeAndMethod = None
        fullCalleeAndMethod = None
        if isinstance(ctx.parentCtx, JavaParser.ExprDotContext):
            calleeAndMethod = self.ast.putDotTogether(self.ast.getNodeByCtx(ctx))

        if calleeAndMethod:
            lastDot = calleeAndMethod.rfind(".")
            callee = calleeAndMethod[0:lastDot]
            logger.debug("HAS CALLEE : " + callee)
            if isUsableExpression(callee):
                self.useList.add(callee)
                logger.debug("CALLEE IS USABLE")
            methodName = calleeAndMethod[lastDot + 1:]
            callExpression = calleeAndMethod

            calleeType = None
            # поиск callee в локальных переменных
            fileQN = self.ast.getProperty("package") + "." +\
                     os.path.splitext(os.path.basename(self.ast.getProperty("filePath")))[0]
            # methodQN = self.packageName + "." + self.activeClasses.peek() + "." + self.currentMethod
            gResp = Gremlin(self.projectConfig).g.V().hasLabel("ASTNode").has("file", fileQN)\
                .has("kind", "METHOD").out().has("kind", "NAME").has("code", str(self.currentMethod)).inE().outV()\
                .repeat(__.out()).until(__.has("kind", "VARIABLE"))\
                .out().has("kind", "NAME").has("code", callee)\
                .inE().outV()\
                .out().has("kind", "TYPE").values("code").toList()
            if len(gResp) > 0:
                assert(len(gResp) == 1)
                calleeType = gResp[0]

            if calleeType is None:
                # поиск callee в свойствах класса
                gResp = Gremlin(self.projectConfig).g.V().hasLabel("ASTNode").has("file", fileQN)\
                    .has("kind", "FIELD").out().has("kind", "NAME").has("code", callee) \
                    .inE().outV() \
                    .out().has("kind", "TYPE").values("code").toList()
                if len(gResp) > 0:
                    assert(len(gResp) == 1)
                    calleeType = gResp[0]

            # определение типа
            # тип стандартный?
            if calleeType is not None:
                if not TypeDeterminator.checkIsBuiltin(calleeType):
                    for qn in self.db.getAllJavaClasses().keys():
                        if qn.split(".")[-1] == calleeType:
                            fullCalleeAndMethod = f"{qn}.{methodName}"
            # тип это класс из проекта?
            # найти в бд джава-классов этот класс. Это и будет callee
            # сконкатенировать callee и methodName
        else:
            logger.debug("NO CALLEE")
            if ctx.IDENTIFIER() is not None:
                methodName = ctx.IDENTIFIER().getText()
            elif ctx.THIS() is not None:
                methodName = "this"
            else:
                methodName = "super"
            callExpression = methodName
            fullCalleeAndMethod = methodName
        defInfo = self.findDefInfo(callee, methodName, ctx.expressionList())
        # logger.debug("FIND DEF RESULT: " + str(defInfo))
        # logger.debug("---")
        if callee is not None and doesMethodStateDef(methodName):
            self.defList.add(callee)



        if self.currentDFG is not None:
            dfParent = getDataFlowParent(self.currentDFG, ctx, self.ast)
            return callExpression + "(" + self.visitMethodArgs(ctx.expressionList(), fullCalleeAndMethod, dfParent) + ")"
        else:
            return callExpression + "(" + self.visit(ctx.expressionList()) + ")"

    def visitExprNew(self, ctx: JavaParser.ExprNewContext):
        # expression: NEW creator         # ExprNew
        # creator
        #     : nonWildcardTypeArguments createdName classCreatorRest
        #     | createdName (arrayCreatorRest | classCreatorRest)
        # createdName
        #     : IDENTIFIER typeArgumentsOrDiamond? ('.' IDENTIFIER typeArgumentsOrDiamond?)*
        #     | primitiveType
        # arrayCreatorRest
        #     : '[' (']' ('[' ']')* arrayInitializer | expression ']' ('[' expression ']')* ('[' ']')*)
        # classCreatorRest
        #     : arguments classBody?

        # 1st process 'createdName'
        creator = None
        rest = None
        if ctx.creator().createdName().primitiveType() is not None:
            creator = ctx.creator().createdName().primitiveType().getText()
        else:
            creator = ctx.creator().createdName().IDENTIFIER()[-1].getText()

        # 2nd process '(arrayCreatorRest | classCreatorRest)'
        if ctx.creator().arrayCreatorRest() is not None:
            if ctx.creator().arrayCreatorRest().arrayInitializer() is not None:
                arrayInitCtx = ctx.creator().arrayCreatorRest().arrayInitializer()
                arrayInit = ""
                for initCtx in arrayInitCtx:
                    init = self.visit(initCtx)
                    if isUsableExpression(init):
                        self.useList.add(init)
                    arrayInit += ", " + init
                rest = "{ " + arrayInit + " }"
            else:
                arrayCreate = ""
                for exprCtx in ctx.creator().arrayCreatorRest().expression():
                    expr = self.visit(exprCtx)
                    if isUsableExpression(expr):
                        self.useList.add(expr)
                    arrayCreate += '[' + expr + ']'
                rest = arrayCreate
        else:
            # class constructor ...
            argsCtx = ctx.creator().classCreatorRest().arguments()
            rest = '(' + self.visitMethodArgs(argsCtx.expressionList()) + ')'
        return "$NEW " + creator + rest

    def visitExprArray(self, ctx: JavaParser.ExprArrayContext):
        # expression '[' expression ']'
        array = self.visit(ctx.expression(0))
        if isUsableExpression(array):
            self.useList.add(array)
        index = self.visit(ctx.expression(1))
        if isUsableExpression(index):
            self.useList.add(index)

        return array + "[" + index + "]"

    def visitExprTernary(self, ctx: JavaParser.ExprTernaryContext):
        # <assoc=right> expression bop='?' expression ':' expression
        prdct = self.visit(ctx.expression(0))
        if isUsableExpression(prdct):
            self.useList.add(prdct)
        retTrue = self.visit(ctx.expression(1))
        if isUsableExpression(retTrue):
            self.useList.add(retTrue)
        retFalse = self.visit(ctx.expression(2))
        if isUsableExpression(retFalse):
            self.useList.add(retFalse)
        return prdct + " ? " + retTrue + " : " + retFalse

    # ***************************************************************
    # ***              DETERMINANT EXPRESSIONS (NO RETURN)        ***
    # ***************************************************************

    def visitExprPostUnaryOp(self, ctx: JavaParser.ExprPostUnaryOpContext):
        # expression postfix=('++' | '--')
        expr = self.visit(ctx.expression())
        if isUsableExpression(expr):
            self.useList.add(expr)
            self.defList.add(expr)

        return expr + ctx.postfix.text

    def visitExprPrePreUnaryOp(self, ctx: JavaParser.ExprPrePreUnaryOpContext):
        # prefix=('+'|'-'|'++'|'--') expression
        expr = self.visit(ctx.expression())
        if isUsableExpression(expr):
            self.useList.add(expr)
            if ctx.prefix == "++" or ctx.prefix == "--":
                self.defList.add(expr)
                self.selfFlowList.add(expr)

        return ctx.prefix.text + expr

    def visitExprNegation(self, ctx: JavaParser.ExprNegationContext):
        # prefix=('~'|'!') expression
        expr = self.visit(ctx.expression())
        if isUsableExpression(expr):
            self.useList.add(expr)

        return ctx.prefix.text + expr

    def visitExprMulDivMod(self, ctx: JavaParser.ExprMulDivModContext):
        # expression bop=('*'|'/'|'%') expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprAddSub(self, ctx: JavaParser.ExprAddSubContext):
        # expression bop=('+'|'-') expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprBitShift(self, ctx: JavaParser.ExprBitShiftContext):
        # expression ('<' '<' | '>' '>' '>' | '>' '>') expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + " $SHIFT " + right_expr + ")"

    def visitExprComparison(self, ctx: JavaParser.ExprComparisonContext):
        # expression bop=('<=' | '>=' | '>' | '<') expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + " $COMP " + right_expr + ")"

    def visitExprInstanceOf(self, ctx: JavaParser.ExprInstanceOfContext):
        # expression bop=INSTANCEOF typeType
        expr = self.visit(ctx.expression())
        return '(' + expr + " $INSTANCE " + ctx.typeType().getText() + ')'

    def visitExprEquality(self, ctx: JavaParser.ExprEqualityContext):
        # expression bop=('==' | '!=') expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + " $EQL " + right_expr + ")"

    def visitExprBitAnd(self, ctx: JavaParser.ExprBitAndContext):
        # expression bop='&' expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprBitXor(self, ctx: JavaParser.ExprBitXorContext):
        # expression bop='^' expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprBitOr(self, ctx: JavaParser.ExprBitOrContext):
        # expression bop='|' expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprLogicAnd(self, ctx: JavaParser.ExprLogicAndContext):
        # expression bop='&&' expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprLogicOr(self, ctx: JavaParser.ExprLogicOrContext):
        # expression bop='||' expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            self.useList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return "(" + left_expr + ctx.bop.text + right_expr + ")"

    def visitExprAssign(self, ctx: JavaParser.ExprAssignContext):
        # <assoc=right> expression
        #       bop=('=' | '+=' | '-=' | '*=' | '/=' | '&=' | '|=' | '^=' | '>>=' | '>>>=' | '<<=' | '%=')
        #       expression
        left_expr = self.visit(ctx.expression(0))
        right_expr = self.visit(ctx.expression(1))
        if isUsableExpression(left_expr):
            if ctx.bop != "=":
                self.useList.add(left_expr)
            self.defList.add(left_expr)
        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return '(' + left_expr + " $ASSIGN " + right_expr + ')'

    def visitVariableDeclarators(self, ctx: JavaParser.VariableDeclaratorsContext):
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*
        vars = ""
        vars += self.visit(ctx.variableDeclarator(0))
        for i in range(1, len(ctx.variableDeclarator())):
            vars += ", " + self.visit(ctx.variableDeclarator(i))

        return vars

    def visitVariableDeclarator(self, ctx: JavaParser.VariableDeclaratorContext):
        # variableDeclarator: variableDeclaratorId ('=' variableInitializer)?
        # variableDeclaratorId: IDENTIFIER ('[' ']')*

        varId = ctx.variableDeclaratorId().IDENTIFIER().getText()

        init = ""
        if ctx.variableInitializer() is not None:
            init = self.visit(ctx.variableInitializer())
            if isUsableExpression(init):
                self.useList.add(init)
            self.defList.add(varId)
            init = " $INIT " + init
        return "$VAR" + varId + init

    def visitVariableInitializer(self, ctx: JavaParser.VariableInitializerContext):
        # variableInitializer: arrayInitializer | expression
        # arrayInitializer: '{' (variableInitializer (',' variableInitializer)* (',')? )? '}'

        if ctx.expression() is not None:
            return self.visit(ctx.expression())

        arrayInit = ""
        for initCtx in ctx.arrayInitializer().variableInitializer():
            init = self.visit(initCtx)
            if isUsableExpression(init):
                self.useList.add(init)

            arrayInit += ", " + init
        return "{" + arrayInit + "}"

    # TODO implement
    def findDefInfo(self, callee: str, methodName: str, ctx: JavaParser.ExpressionListContext) -> JavaMethod:
        # return self.methodDEFs.get(name)  # Будем пока считать, что методов с одинаковыми именами нет
        qualifiedClassName = f"{self.packageName}.{self.activeClasses.peek().name}"
        return self.db.getMethod(qualifiedClassName, methodName)
        # logger.debug("METHOD NAME: " + name)
        # logger.debug("# found = " + str(0 if not lst else len(lst)))
        #
        # if lst is None:
        #     return None
        #
        # if len(lst) == 1:
        #     logger.debug("SINGLE CANDIDATE")
        #     mtd = lst[0]
        #     # just check params-count to make sure
        #     if ctx is not None and mtd.PARAM_TYPES is not None and len(mtd.PARAM_TYPES) != len(ctx.expression()):
        #         return None
        #     logger.debug("WITH MATCHING PARAMS COUNT")
        #     return mtd
        #
        # if callee is None:
        #     logger.debug("NO CALLEE")
        #     for mtd in lst:
        #         if mtd.PACKAGE != self.activeClasses.peek().PACKAGE:
        #             continue
        #
        #         classNameMatch = False
        #         for cls in self.activeClasses:
        #             if mtd.CLASS_NAME == cls.NAME:
        #                 classNameMatch = True
        #                 break
        #         if not classNameMatch:
        #             continue
        #
        #         if ctx is not None and mtd.PARAM_TYPES is not None and len(mtd.PARAM_TYPES) != len(ctx.expression()):
        #             continue
        #
        #         if ctx is not None:
        #             argTypes = []
        #             for arg in self.visit(ctx.expression()):
        #                 argTypes.append(getType(arg))
        #             if mtd.PARAM_TYPES is not None:
        #                 pass

    def getType(self, Id: str):
        ''' Return type of a given symbol
        Returns null if symbol not found

        :param Id:
        :return:
        '''
        if isUsableExpression(Id):
            for param in self.methodParams:
                if param.name == Id:
                    return param.type
            for local in self.localVars:
                if local.name == Id:
                    return local.type
            if Id.startswith("this."):
                Id = Id[4:]

            for field in self.activeClasses.peek().getAllFields():
                if field.name == Id:
                    return field.type

            for cls in self.activeClasses:
                for field in cls.getAllFields():
                    if field.name == Id:
                        return field.type

            logger.debug("getType(" + Id + ") : is USABLE but NOT DEFINED")
            return None
        else:
            logger.debug("getType(" + Id + ") : is USABLE but NOT DEFINED")
            return None

    def getDFG(self, qualifiedName):
        return self.ddgs[qualifiedName]