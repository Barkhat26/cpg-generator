import os
from pathlib import Path

from antlr4.ParserRuleContext import ParserRuleContext

from graph_dsl import Query, __
from graphs.ast.abstract_syntax_tree_nx import AbstractSyntaxTreeNX
from graphs.cfg.control_flow_graph_nx import ControlFlowGraphNX
from java.type_determinator import TypeDeterminator
from antlr.JavaParser import JavaParser
from antlr.JavaParserVisitor import JavaParserVisitor
from graphs.ddg.dfg_node import DFNode
from graphs.ddg.data_flow_graph_nx import DataFlowGraphNX
from utils.datatypes import Stack
from utils.other import build_method_qn
from utils.parsing import getIdByCtx, getOriginalCodeText
from utils.dataflow import isUsableExpression, doesMethodStateDef
from java.java_structures import JavaField, MethodDefInfo, JavaMethod, JavaClass
from log import dfg_visitor_logger as logger


class DFGVisitor(JavaParserVisitor):
    def __init__(self,
                 iteration: int,
                 ddg: DataFlowGraphNX,
                 cfg: ControlFlowGraphNX,
                 ast: AbstractSyntaxTreeNX,
                 java_classes: dict[str, JavaClass],
                 file_path: Path | str = None):
        self.analysis_visit = False
        self.iteration = iteration
        self.ddg = ddg
        self.ast = ast
        self.cfg = cfg
        self.java_classes = java_classes
        self.localVars: list[JavaField] = []
        self.useList: set[str] = set()
        self.defList: set[str] = set()
        self.selfFlowList: set[str] = set()
        self.changed = False
        self.methodParams = []
        self.activeClasses = Stack(JavaClass)
        self.filePath = file_path

        self.currentMethod: str | None = None
        self.packageName: str | None = None

    def analyseDefUse(self, node: DFNode, node_ctx: ParserRuleContext):
        logger.debug("--- ANALYSIS ---")
        logger.debug(node)
        self.analysis_visit = True
        expr: str = self.visit(node_ctx)
        # TODO: избавиться
        node = self.ddg.get_node_by_id(node.Id)
        logger.debug(expr)

        local_var_str = ""
        local_var_str += "LOCAL VARS = ["
        for lv in self.localVars:
            local_var_str += lv.type + " " + lv.name + ", "
        local_var_str += "]"
        logger.debug(local_var_str)

        if isUsableExpression(expr):
            self.useList.add(expr)
            logger.debug("USABLE")

        self.analysis_visit = False
        logger.debug("Changed = " + str(self.changed))
        logger.debug("DEFs = " + ' '.join(node.defs))
        logger.debug("USEs = " + ' '.join(node.uses))

        for DEF in self.defList:
            status = self.isDefined(DEF)
            if status > -1:
                self.changed |= node.add_def(DEF)
                self.ddg.update_node(node)
            else:
                logger.debug(f"{DEF} is not defined!")

        logger.debug("Changed = " + str(self.changed))
        logger.debug("DEFs = " + ' '.join(node.defs))

        for USE in self.useList:
            status = self.isDefined(USE)
            if status > -1:
                self.changed |= node.add_use(USE)
                self.ddg.update_node(node)
            else:
                logger.debug(f"{USE} is not defined!")

        logger.debug("Changed = " + str(self.changed))
        logger.debug("USEs = " + ' '.join(node.uses))

        for selfFlow in self.selfFlowList:
            status = self.isDefined(selfFlow)
            if status > -1:
                self.changed |= node.add_self_flow(selfFlow)
                self.ddg.update_node(node)
            else:
                logger.debug(f"{selfFlow} is not defined!")

        logger.debug("Changed = " + str(self.changed))
        logger.debug("SelfFlows = " + ' '.join(node.self_flows))
        logger.debug("----------------")

        self.defList.clear()
        self.useList.clear()
        self.selfFlowList.clear()

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

        # TODO: изменить итерацию стека
        for cls in self.activeClasses._items:
            for field in cls.fields:
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

        class_name = ctx.IDENTIFIER().getText()
        qualified_name = f"{self.packageName}.{class_name}" if self.packageName else class_name
        cls = self.java_classes.get(qualified_name)

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
            self.currentMethod = ctx.IDENTIFIER().getText()
            entry = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code=ctx.IDENTIFIER().getText() + getOriginalCodeText(ctx.formalParameters()),
                shared_id=self.calculate_shared_id(ctx),
                optional_properties={'name': self.currentMethod, 'class': self.activeClasses.peek().name}
            )

            # Extract all parameters and IDs
            param_ids = []
            param_types = []

            if ctx.formalParameters().formalParameterList() is not None:
                for prm in ctx.formalParameters().formalParameterList().formalParameter():
                    param_types.append(self.visitTypeType(prm.typeType()))
                    param_ids.append(prm.variableDeclaratorId().IDENTIFIER().getText())

                last_param = ctx.formalParameters().formalParameterList().lastFormalParameter()

                if last_param is not None:
                    param_types.append(self.visitTypeType(last_param.typeType()))
                    param_ids.append(last_param.variableDeclaratorId().IDENTIFIER().getText())

            self.methodParams = []

            for i in range(len(param_types)):
                self.methodParams.append(JavaField(
                    None, False, param_types[i], param_ids[i]
                ))
            # entry.setProperty("params", self.methodParams)

            # Adding DEFs for input parameters
            for pid in param_ids:
                self.changed |= entry.add_def(pid)
                self.ddg.update_node(entry)
        else:
            self.currentMethod = ctx.IDENTIFIER().getText()

        self.localVars.clear()
        if ctx.constructorBody is not None:
            self.visit(ctx.constructorBody)
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
            ret_type = ctx.typeTypeOrVoid().getText()
            self.currentMethod = ctx.IDENTIFIER().getText()
            entry = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code=ret_type + " " + self.currentMethod + getOriginalCodeText(ctx.formalParameters()),
                shared_id=self.calculate_shared_id(ctx),
                optional_properties={'name': self.currentMethod, 'type': ret_type, "class": self.activeClasses.peek().name}
            )

            # Extract all parameters and IDs
            param_ids = []
            param_types = []

            if ctx.formalParameters().formalParameterList() is not None:
                for prm in ctx.formalParameters().formalParameterList().formalParameter():
                    param_types.append(self.visitTypeType(prm.typeType()))
                    param_ids.append(prm.variableDeclaratorId().IDENTIFIER().getText())

                last_param = ctx.formalParameters().formalParameterList().lastFormalParameter()

                if last_param is not None:
                    param_types.append(self.visitTypeType(last_param.typeType()))
                    param_ids.append(last_param.variableDeclaratorId().IDENTIFIER().getText())

            self.methodParams = []

            for i in range(len(param_types)):
                self.methodParams.append(JavaField(
                    None, False, param_types[i], param_ids[i]
                ))
            # entry.setProperty("params", self.methodParams)

            # Adding DEFs for input parameters
            for pid in param_ids:
                self.changed |= entry.add_def(pid)
                self.ddg.update_node(entry)
        else:
            self.currentMethod = ctx.IDENTIFIER().getText()

        self.localVars.clear()
        if ctx.methodBody() is not None:
            self.visit(ctx.methodBody())
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

        for var_declarator_ctx in ctx.variableDeclarators().variableDeclarator():
            self.localVars.append(JavaField(
                None,
                False,
                self.visit(ctx.typeType()),
                var_declarator_ctx.variableDeclaratorId().IDENTIFIER().getText()
            ))

            if self.analysis_visit:
                return self.visit(ctx.variableDeclarators())

            if self.iteration == 1:
                declarator = self.ddg.add_node(
                    line=var_declarator_ctx.start.line,
                    file=self.filePath,
                    method=self.currentMethod,
                    code=getOriginalCodeText(var_declarator_ctx),
                    shared_id=self.calculate_shared_id(var_declarator_ctx)
                )
            else:
                declarator = self.ddg.get_node_by_shared_id(self.calculate_shared_id(var_declarator_ctx))

            self.analyseDefUse(declarator, var_declarator_ctx)
        return None

    # ************************************************************
    # ************    STATEMENTS *********************************
    # ************************************************************

    def visitBlock(self, ctx: JavaParser.BlockContext):
        # block: '{' blockStatement* '}'

        # Local vars defined inside a block, are only valid till the end of that block.
        entry_size = len(self.localVars)
        self.visitChildren(ctx)
        if len(self.localVars) > entry_size:
            del self.localVars[entry_size:]
        return None

    def visitStmtExpr(self, ctx: JavaParser.StmtExprContext):
        # expression ';'

        if self.analysis_visit:
            return self.visit(ctx.expression())

        if self.iteration == 1:
            expr = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code=getOriginalCodeText(ctx),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            expr = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        self.analyseDefUse(expr, ctx.expression())
        return None

    def visitStmtIf(self, ctx: JavaParser.StmtIfContext):
        # IF parExpression trueClause=statement (ELSE falseClause=statement)?

        if self.iteration == 1:
            if_node = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code="if " + getOriginalCodeText(ctx.parExpression()),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            if_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        self.analyseDefUse(if_node, ctx.parExpression().expression())
        self.visit(ctx.trueClause)

        if ctx.falseClause is not None:
            self.visit(ctx.falseClause)

        return None

    def visitStmtFor(self, ctx: JavaParser.StmtForContext):
        # FOR '(' forControl ')' statement

        entry_size = len(self.localVars)
        # First, we should check type of for-loop ...
        if (enhanced_for_ctx := ctx.forControl().enhancedForControl()) is not None:
            # enhancedForControl: variableModifier* typeType variableDeclaratorId ':' expression

            if self.iteration == 1:
                for_expr = self.ddg.add_node(
                    line=enhanced_for_ctx.start.line,
                    file=self.filePath,
                    method=self.currentMethod,
                    code="for (" + getOriginalCodeText(enhanced_for_ctx) + ")",
                    shared_id=self.calculate_shared_id(enhanced_for_ctx)
                )
            else:
                for_expr = self.ddg.get_node_by_shared_id(self.calculate_shared_id(enhanced_for_ctx))

            # Now analyse DEF-USE by visiting the expression ...
            var_type = self.visitTypeType(enhanced_for_ctx.typeType())
            var_name = enhanced_for_ctx.variableDeclaratorId().IDENTIFIER().getText()
            self.localVars.append(JavaField(None, False, var_type, var_name))
            self.changed |= for_expr.add_def(var_name)
            self.ddg.update_node(for_expr)
            self.analyseDefUse(for_expr, enhanced_for_ctx.expression())
        else:
            # forInit? ';' expression? ';' forUpdate=expressionList?

            if (for_init_ctx := ctx.forControl().forInit()) is not None:
                if self.iteration == 1:
                    for_init = self.ddg.add_node(
                        line=for_init_ctx.start.line,
                        file=self.filePath,
                        method=self.currentMethod,
                        code=getOriginalCodeText(for_init_ctx),
                        shared_id=self.calculate_shared_id(for_init_ctx)
                    )
                else:
                    for_init = self.ddg.get_node_by_shared_id(self.calculate_shared_id(for_init_ctx))

                # Now analyse DEF-USE by visiting the expression ...
                if ctx.forControl().forInit().expressionList() is not None:
                    self.analyseDefUse(for_init, ctx.forControl().forInit().expressionList())
                else:
                    self.analyseDefUse(for_init, ctx.forControl().forInit().localVariableDeclaration())

            if (for_expr_ctx := ctx.forControl().expression()) is not None:
                if self.iteration == 1:
                    for_expr = self.ddg.add_node(
                        line=for_expr_ctx.start.line,
                        file=self.filePath,
                        method=self.currentMethod,
                        code="for (" + getOriginalCodeText(for_expr_ctx) + ")",
                        shared_id=self.calculate_shared_id(for_expr_ctx)
                    )
                else:
                    for_expr = self.ddg.get_node_by_shared_id(self.calculate_shared_id(for_expr_ctx))

                # Now analyse DEF-USE by visiting the expression ...
                self.analyseDefUse(for_expr, ctx.forControl().expression())

            if (for_update_ctx := ctx.forControl().forUpdate) is not None:
                if self.iteration == 1:
                    for_update = self.ddg.add_node(
                        line=for_update_ctx.start.line,
                        file=self.filePath,
                        method=self.currentMethod,
                        code=getOriginalCodeText(for_update_ctx),
                        shared_id=self.calculate_shared_id(for_update_ctx)
                    )
                else:
                    for_update = self.ddg.get_node_by_shared_id(for_update_ctx)

                # Now analyse DEF-USE by visiting the expression ...
                self.analyseDefUse(for_update, ctx.forControl().forUpdate)

        # visit loop body
        visit = self.visit(ctx.statement())

        # clear any local vars defined in the for loop
        if len(self.localVars) > entry_size:
            del self.localVars[entry_size:]

        return visit

    def visitStmtWhile(self, ctx: JavaParser.StmtWhileContext):
        # WHILE parExpression statement

        if self.iteration == 1:
            while_node = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code="while " + getOriginalCodeText(ctx.parExpression()),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            while_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(while_node, ctx.parExpression().expression())
        return self.visit(ctx.statement())

    def visitStmtDoWhile(self, ctx: JavaParser.StmtDoWhileContext):
        # DO statement WHILE parExpression ';'

        self.visit(ctx.statement())

        if self.iteration == 1:
            while_node = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code="while " + getOriginalCodeText(ctx.parExpression()),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            while_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(while_node, ctx.parExpression().expression())
        return None

    def visitStmtSwitch(self, ctx: JavaParser.StmtSwitchContext):
        # SWITCH parExpression '{' switchBlockStatementGroup* switchLabel* '}'
        # switchBlockStatementGroup : switchLabel+ blockStatement+

        if self.iteration == 1:
            switch_node = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code="switch " + getOriginalCodeText(ctx.parExpression()),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            switch_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(switch_node, ctx.parExpression().expression())

        for scx in ctx.switchBlockStatementGroup():
            self.visit(scx)

        for scx in ctx.switchLabel():
            self.visit(scx)

        return None

    def visitStmtReturn(self, ctx: JavaParser.StmtReturnContext):
        # RETURN expression? ';'

        if self.iteration == 1:
            ret = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code=getOriginalCodeText(ctx),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            ret = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        # Now analyse DEF-USE by visiting the expression ...
        if ctx.expression() is not None:
            self.analyseDefUse(ret, ctx.expression())

        return None

    def visitStmtSynchronized(self, ctx: JavaParser.StmtSynchronizedContext):
        # SYNCHRONIZED parExpression block

        if self.iteration == 1:
            sync_stmt = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code="synchronized " + getOriginalCodeText(ctx.parExpression()),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            sync_stmt = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(sync_stmt, ctx.parExpression().expression())

        return self.visit(ctx.block())

    def visitStmtThrow(self, ctx: JavaParser.StmtThrowContext):
        # THROW expression ';'

        if self.iteration == 1:
            throw_node = self.ddg.add_node(
                line=ctx.start.line,
                file=self.filePath,
                method=self.currentMethod,
                code="throw " + getOriginalCodeText(ctx.expression()),
                shared_id=self.calculate_shared_id(ctx)
            )
        else:
            throw_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(ctx))

        # Now analyse DEF-USE by visiting the expression ...
        self.analyseDefUse(throw_node, ctx.expression())
        return None

    def visitStmtTry(self, ctx: JavaParser.StmtTryContext):
        # TRY block (catchClause+ finallyBlock? | finallyBlock)

        # The 'try' block has no DEF-USE effect, so no need for DFNodes;
        # just visit the 'block'
        self.visit(ctx.block())

        # But the 'catchClause' define a local exception variable;
        # so we need to visit any available catch clauses
        if (catch_clause_ctx := ctx.catchClause()) is not None and len(ctx.catchClause()) > 0:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block

            for cx in catch_clause_ctx:
                if self.iteration == 1:
                    catch_node = self.ddg.add_node(
                        line=cx.start.line,
                        file=self.filePath,
                        method=self.currentMethod,
                        code="catch (" + cx.catchType().getText() + cx.IDENTIFIER().getText() + ")",
                        shared_id=self.calculate_shared_id(cx)
                    )
                else:
                    catch_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(cx))

                # Define the exception var
                var_type = cx.catchType().getText()
                var_name = cx.IDENTIFIER().getText()
                exception_var = JavaField(None, False, var_type, var_name)
                self.localVars.append(exception_var)
                self.changed |= catch_node.add_def(var_name)
                self.ddg.update_node(catch_node)

                self.visit(cx.block())
                self.localVars.remove(exception_var)

        if (finally_block_ctx := ctx.finallyBlock()) is not None:
            # finallyBlock: FINALLY block

            self.visit(finally_block_ctx.block())

        return None

    def visitStmtTryResource(self, ctx: JavaParser.StmtTryResourceContext):
        # TRY resourceSpecification block catchClause* finallyBlock?
        # resourceSpecification: '(' resources ';'? ')'
        # resources: resource (';' resource)*
        # resource: variableModifier* classOrInterfaceType variableDeclaratorId '=' expression

        entry_size = len(self.localVars)

        # Analyze all resources
        for rsrx in ctx.resourceSpecification().resources().resource():
            if self.iteration == 1:
                resource = self.ddg.add_node(
                    line=rsrx.start.line,
                    file=self.filePath,
                    method=self.currentMethod,
                    code=getOriginalCodeText(rsrx),
                    shared_id=self.calculate_shared_id(rsrx)
                )
            else:
                resource = self.ddg.get_node_by_shared_id(self.calculate_shared_id(rsrx))

            # Define the resource variable
            var_type = rsrx.classOrInterfaceType().getText()
            var_name = rsrx.variableDeclaratorId().getText()
            self.localVars.append(JavaField(None, False, var_type, var_name))

            # Now analyse DEF-USE by visiting the expression ...
            self.analyseDefUse(resource, rsrx)

        # The 'try' block has no DEF-USE effect, so no need for DFNodes;
        # just visit the 'block'
        self.visit(ctx.block())

        # But the 'catchClause' define a local exception variable;
        # so we need to visit any available catch clauses
        if (catch_clause_ctx := ctx.catchClause()) is not None and len(ctx.catchClause()) > 0:
            # catchClause: CATCH '(' variableModifier* catchType IDENTIFIER ')' block
            for cx in catch_clause_ctx:
                if self.iteration == 1:
                    catch_node = self.ddg.add_node(
                        line=cx.start.line,
                        file=self.filePath,
                        method=self.currentMethod,
                        code="catch (" + cx.catchType().getText() + cx.IDENTIFIER().getText() + ")",
                        shared_id=self.calculate_shared_id(cx)
                    )
                else:
                    catch_node = self.ddg.get_node_by_shared_id(self.calculate_shared_id(cx))

                # Define the exception var
                var_type = cx.catchType().getText()
                var_name = cx.IDENTIFIER().getText()
                exception_var = JavaField(None, False, var_type, var_name)
                self.localVars.append(exception_var)
                self.changed |= catch_node.add_def(var_name)
                self.ddg.update_node(catch_node)

                self.visit(cx.block())
                self.localVars.remove(exception_var)

        if ctx.finallyBlock() is not None:
            # finallyBlock: FINALLY block
            self.visit(ctx.finallyBlock().block())

        # Remove resources from local vars ...
        if len(self.localVars) > entry_size:
            del self.localVars[entry_size:]

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
            # return self.visit(ctx.expression()) + "." + self.visit(ctx.methodCall())
            return self.visit(ctx.methodCall())

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
            args_ctx = ctx.innerCreator().classCreatorRest().arguments()
            rest = self.visitMethodArgs(args_ctx)
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
            suffix_ctx = ctx.explicitGenericInvocation().explicitGenericInvocationSuffix()
            if suffix_ctx.IDENTIFIER() is not None:
                invoc_suffix = suffix_ctx.IDENTIFIER().getText()
                invoc_suffix += '(' + self.visitMethodArgs(suffix_ctx.arguments().expressionList()) + ')'
            else:
                invoc_suffix = "super"
                if suffix_ctx.superSuffix().Identifier() is not None:
                    invoc_suffix += '.' + suffix_ctx.superSuffix().IDENTIFIER().getText()
                if suffix_ctx.superSuffix().arguments() is not None:
                    invoc_suffix += '(' + self.visitMethodArgs(suffix_ctx.superSuffix().arguments().expressionList()
                                                              ) + ')'
            return expression + '.' + ctx.explicitGenericInvocation().nonWildcardTypeArguments().getText() + invoc_suffix

        return self.visit(ctx.expression()) + ".UNKNOWN"

    def visitExprCasting(self, ctx: JavaParser.ExprCastingContext):
        # expression: '(' typeType ')' expression

        return "$CAST(" + self.visit(ctx.typeType()) + ")" + self.visit(ctx.expression())

    def visitExpressionList(self, ctx: JavaParser.ExpressionListContext):
        # expressionList: expression (',' expression)*

        expr = self.visit(ctx.expression(0))
        if isUsableExpression(expr):
            self.useList.add(expr)
        exp_list = expr
        for i in range(1, len(ctx.expression())):
            expr = self.visit(ctx.expression(i))
            if isUsableExpression(expr):
                self.useList.add(expr)
            exp_list += ", " + expr
        return exp_list

    # *************************************************************
    # *** DETERMINANT EXPRESSIONS (RETURN OBJECT) ***
    # *************************************************************

    # Visit the list of arguments of a method call, and return a proper string.
    # This method will also add usable expressions to the USE-list.
    def visitMethodArgs(self, ctx: JavaParser.ExpressionListContext, method_name: str | None = None, call_node: DFNode | None = None):
        # expressionList: expression (',' expression)*
        if ctx is not None:
            args = ""
            arg_list = ctx.expression()
            arg = self.visit(arg_list[0])
            if isUsableExpression(arg):
                self.useList.add(arg)
                # if defInfo is not None and defInfo.argDEFs[0]:
                #     self.defList.add(arg)

                # if methodName is not None:
                #     callNode.IP_DEFs = {
                #         "methodName": methodName,
                #         "edges": [arg + "-"]
                #     }

            if method_name is not None:
                lookup_method_name = method_name if "." in method_name \
                    else build_method_qn(self.packageName, self.activeClasses.peek().name, method_name)

                if entry := self.cfg.entries.get(lookup_method_name):
                    call_node.ip_defs = {
                        "entrySharedId": entry.shared_id
                    }
                    self.ddg.update_node(call_node)

            for i in range(1, len(arg_list)):
                arg = self.visit(arg_list[i])
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
        callee_and_method = None
        full_callee_and_method = None

        if isinstance(ctx.parentCtx, JavaParser.ExprDotContext):
            callee_and_method = self.ast.put_dot_together(self.ast.get_node_by_shared_id(self.calculate_shared_id(ctx)))

        if callee_and_method:
            last_dot = callee_and_method.rfind(".")
            callee = callee_and_method[0:last_dot]
            logger.debug("HAS CALLEE : " + callee)

            if isUsableExpression(callee):
                self.useList.add(callee)
                logger.debug("CALLEE IS USABLE")

            method_name = callee_and_method[last_dot + 1:]
            call_expression = callee_and_method

            callee_type = None
            # поиск callee в локальных переменных
            if package := self.ast.get_property("package"):
                prefix = package + "."
            else:
                prefix = ""
            file_qn = prefix + os.path.splitext(os.path.basename(self.ast.get_property("filePath")))[0] \
                if self.ast.get_property("filePath") else None
            # methodQN = self.packageName + "." + self.activeClasses.peek() + "." + self.currentMethod

            # gResp = Gremlin(self.projectConfig).g.V().hasLabel("ASTNode").has("file", file_qn)\
            #     .has("kind", "METHOD").out().has("kind", "NAME").has("code", str(self.currentMethod)).inE().outV()\
            #     .repeat(__.out()).until(__.has("kind", "VARIABLE"))\
            #     .out().has("kind", "NAME").has("code", callee)\
            #     .inE().outV()\
            #     .out().has("kind", "TYPE").values("code").toList()
            gResp = Query(self.ast.g)\
                .V()\
                .has("file", file_qn)\
                .has("kind", "METHOD")\
                .out()\
                .has("kind", "NAME")\
                .has("code", str(self.currentMethod))\
                .inE()\
                .outV()\
                .repeat(__.out())\
                .until(__.has("kind", "VARIABLE"))\
                .out()\
                .has("kind", "NAME")\
                .has("code", callee)\
                .inE()\
                .outV()\
                .out()\
                .has("kind", "TYPE")\
                .values("code")
            # gResp = self._find_type_of_variable(self.ast.g, file_qn, self.currentMethod, callee)

            if len(gResp) > 0:
                assert(len(gResp) == 1)
                callee_type = gResp[0]

            if callee_type is None:
                # поиск callee в свойствах класса
                # gResp = Gremlin(self.projectConfig).g.V().hasLabel("ASTNode").has("file", file_qn)\
                #     .has("kind", "FIELD").out().has("kind", "NAME").has("code", callee) \
                #     .inE().outV() \
                #     .out().has("kind", "TYPE").values("code").toList()
                gResp = Query(self.ast.g)\
                    .V()\
                    .has("file", file_qn)\
                    .has("kind", "FIELD")\
                    .out()\
                    .has("kind", "NAME")\
                    .has("code", callee)\
                    .inE()\
                    .outV()\
                    .out()\
                    .has("kind", "TYPE")\
                    .values("code")
                # gResp = self._find_field_type(self.ast.g, file_qn, callee)
                if gResp:
                    assert(len(gResp) == 1)
                    callee_type = gResp[0]

            # определение типа
            # тип стандартный?
            if callee_type is not None:
                if not TypeDeterminator.checkIsBuiltin(callee_type):
                    for qn in self.java_classes:
                        if qn.split(".")[-1] == callee_type:
                            full_callee_and_method = f"{qn}.{method_name}"
            # тип это класс из проекта?
            # найти в бд джава-классов этот класс. Это и будет callee
            # сконкатенировать callee и methodName
        else:
            logger.debug("NO CALLEE")
            if ctx.IDENTIFIER() is not None:
                method_name = ctx.IDENTIFIER().getText()
            elif ctx.THIS() is not None:
                method_name = "this"
            else:
                method_name = "super"
            call_expression = method_name
            full_callee_and_method = method_name
        def_info = self.findDefInfo(callee, method_name, ctx.expressionList())
        # logger.debug("FIND DEF RESULT: " + str(defInfo))
        # logger.debug("---")
        if callee is not None and doesMethodStateDef(method_name):
            self.defList.add(callee)

        if self.ddg is not None:
            df_parent = self.ddg.get_data_flow_parent(self.calculate_shared_id(ctx), self.ast)
            return call_expression + "(" + self.visitMethodArgs(ctx.expressionList(), full_callee_and_method, df_parent) + ")"
        else:
            return call_expression + "(" + self.visit(ctx.expressionList()) + ")"

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
                array_init_ctx = ctx.creator().arrayCreatorRest().arrayInitializer()
                array_init = ""
                for initCtx in array_init_ctx:
                    init = self.visit(initCtx)
                    if isUsableExpression(init):
                        self.useList.add(init)
                    array_init += ", " + init
                rest = "{ " + array_init + " }"
            else:
                array_create = ""
                for exprCtx in ctx.creator().arrayCreatorRest().expression():
                    expr = self.visit(exprCtx)
                    if isUsableExpression(expr):
                        self.useList.add(expr)
                    array_create += '[' + expr + ']'
                rest = array_create
        else:
            # class constructor ...
            args_ctx = ctx.creator().classCreatorRest().arguments()
            rest = '(' + self.visitMethodArgs(args_ctx.expressionList()) + ')'
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
        predicate = self.visit(ctx.expression(0))

        if isUsableExpression(predicate):
            self.useList.add(predicate)

        ret_true = self.visit(ctx.expression(1))

        if isUsableExpression(ret_true):
            self.useList.add(ret_true)

        ret_false = self.visit(ctx.expression(2))

        if isUsableExpression(ret_false):
            self.useList.add(ret_false)

        return predicate + " ? " + ret_true + " : " + ret_false

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
            self.defList.add(left_expr)

            # if augmented assignment
            if ctx.bop != "=":
                self.useList.add(left_expr)

        if isUsableExpression(right_expr):
            self.useList.add(right_expr)

        return '(' + left_expr + " $ASSIGN " + right_expr + ')'

    def visitVariableDeclarators(self, ctx: JavaParser.VariableDeclaratorsContext):
        # variableDeclarators: variableDeclarator (',' variableDeclarator)*

        return ", ".join((self.visit(var_declarator) for var_declarator in ctx.variableDeclarator()))

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
        return "$VAR " + varId + init

    def visitVariableInitializer(self, ctx: JavaParser.VariableInitializerContext):
        # variableInitializer: arrayInitializer | expression
        # arrayInitializer: '{' (variableInitializer (',' variableInitializer)* (',')? )? '}'

        if ctx.expression() is not None:
            return self.visit(ctx.expression())

        array_init = ""
        for initCtx in ctx.arrayInitializer().variableInitializer():
            init = self.visit(initCtx)
            if isUsableExpression(init):
                self.useList.add(init)

            array_init += ", " + init
        return "{" + array_init + "}"

    # TODO implement
    def findDefInfo(self, callee: str, method_name: str, ctx: JavaParser.ExpressionListContext) -> JavaMethod:
        # return self.methodDEFs.get(name)  # Будем пока считать, что методов с одинаковыми именами нет
        qualified_class_name = f"{self.packageName}.{self.activeClasses.peek().name}" if self.packageName else self.activeClasses.peek().name
        return self.java_classes.get(qualified_class_name).get_method_by_name(method_name)  # TODO: здесь может быть NRE
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

    def getType(self, id_: str):
        ''' Return type of a given symbol
        Returns null if symbol not found

        :param id_:
        :return:
        '''
        if isUsableExpression(id_):
            for param in self.methodParams:
                if param.name == id_:
                    return param.type
            for local in self.localVars:
                if local.name == id_:
                    return local.type
            if id_.startswith("this."):
                id_ = id_[4:]

            for field in self.activeClasses.peek().fields:
                if field.name == id_:
                    return field.type

            for cls in self.activeClasses._items: # TODO: итератор
                for field in cls.fields:
                    if field.name == id_:
                        return field.type

            logger.debug("getType(" + id_ + ") : is USABLE but NOT DEFINED")
            return None
        else:
            logger.debug("getType(" + id_ + ") : is USABLE but NOT DEFINED")
            return None

    def calculate_shared_id(self, ctx):
        return getIdByCtx(ctx, self.filePath)