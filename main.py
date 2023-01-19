import logging
import os
import sys
from pprint import pprint
from marshmallow import pprint as mapprint
from gremlin_python.process.graph_traversal import __
from ASTBuilder import ASTBuilder
from CFEngine import CFEngine
from CFGBuilder import CFGBuilder
from DFGBuilder import DFGBuilder
from Engine import Engine
from GremlinDriver import Gremlin
from JavaClassExtractor import JavaClassExtractor
from OrientDBDriver import OrientDB
from config import Config
from db import Database, DBCollections
from graphs.CallGraph import CallGraph
from graphs.ast.ASNode import ASNodeKind
from graphs.cfg.CFPathTraversal import CFPathTraversal
from graphs.cpg.CodePropertyGraph import CodePropertyGraph
from graphs.ast.AbstractSyntaxTree import AbstractSyntaxTree
from graphs.cpg.ControlFlowChain import ControlFlowChain
from graphs.ddg.DFNode import DFNode
from KnowledgeBase import methodToArgTypes
from graphs.digraph import Edge
from schemas import ControlFlowGraphSchema
from sinkPatterns import findCreateQuery
from sourcePatterns import findGetLogin


def getSourceType(dfSource: DFNode):
    from db import Database
    currentAST = None
    for AST in Database().getAllASTs().values():
        if AST.getNodeByID(dfSource.sharedId):
            currentAST = AST
            break

    if currentAST is None:
        return None

    decl = currentAST.getNodeByID(dfSource.sharedId)
    for on in currentAST.outNodes(decl):
        if on.kind == ASNodeKind.TYPE:
            return on.getCode()
    return None


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    if sys.argv[1] == "ast":
        ast = ASTBuilder.build(Config.SINGLE_FILE)
        packageName = ast.getProperty("package")
        baseName = os.path.splitext(os.path.basename(Config.SINGLE_FILE))[0]
        ast.exportSVG(f"{packageName}.{baseName}")
        logger.info("Dumping database...")
        Database().commit()
    elif sys.argv[1] == "cfg":
        cfgs = CFGBuilder.build(Config.SINGLE_FILE)
        # db = Database()
        for methodName, cfg in cfgs.items():
            # db.putCFG("main", ControlFlowGraphSchema().dump(cfg))
            cfg.exportSVG(filename=methodName)
            # newCFG = db.getCFG("main")
            # print(cfg == newCFG)
        logger.info("Dumping database...")
        Database().commit()
    elif sys.argv[1] == "dfg":
        logger.info("Handling: " + Config.SINGLE_FILE)
        logger.info("Building DFGs...")
        cfgs = Database().getCFGsByFilePath(Config.SINGLE_FILE)

        # Если нет функций и их CFG, то следовательно нет и DFG
        if len(cfgs) == 0:
            exit()

        ast = Database().getASTByFilePath(Config.SINGLE_FILE)
        dfgs = DFGBuilder.build(Config.SINGLE_FILE, ast)
        for qn, DFG in dfgs.items():
            DFG.exportSVG(filename=qn)
        logger.info("Dumping database...")
        Database().commit()
    elif sys.argv[1] == "all":
        ast = ASTBuilder.build(Config.SINGLE_FILE)
        cfgs = CFGBuilder.build(Config.SINGLE_FILE)
        dfgs = DFGBuilder.build(Config.SINGLE_FILE, cfgs, ast)
        for methodName, dfg in dfgs.items():
            # db.putCFG("main", ControlFlowGraphSchema().dump(cfg))
            dfg.exportSVG(filename=methodName)
    elif sys.argv[1] == "populatedb":
        JavaClassExtractor.extractInfo(Config.SINGLE_FILE)
        ast = ASTBuilder.build(Config.SINGLE_FILE)
        ast.exportGraphML(Config.SINGLE_FILE)
        cfgs = CFGBuilder.build(Config.SINGLE_FILE)
        for methodName, CFG in cfgs.items():
            CFG.exportGraphML(filename=methodName)
        dfgs = DFGBuilder.build(Config.SINGLE_FILE, ast)
    elif sys.argv[1] == "taint":
        # ast = ASTBuilder.build(filename)
        # cfgs = CFGBuilder.build(filename)
        # # cfg.attachAST(ast)
        # # methodToCFG = cfg.getMethodsToCFG()
        # dfgs = DFGBuilder.build(filename, cfgs, ast)
        cpg = CodePropertyGraph()

        sourceName = "userInput"
        sinkName = "printlnEvil"

        # callSources = cpg.calls(sourceName)
        sources = findGetLogin()

        if len(sources) == 0:
            logger.info(f"Sources 'getLogin()' not found")
            exit(0)

        # callSinks = cpg.calls(sinkName)
        sinks = findCreateQuery()

        if len(sinks) == 0:
            logger.info(f"Sinks 'createQuery()' not found")
            exit(0)

        sinkArgType = methodToArgTypes[sinkName][0]

        subgraph = None
        sourceType = None
        dfsp = None
        dftp = None
        for source in sources:
            logger.info(f"Analyzing call SOURCE with name 'getLogin()' at line {source.line} in {source.file}")
            dfsp, sourceDFGName = Gremlin().findASTNodeInDFG(source.sharedId)
            sourceType = getSourceType(dfsp)
            for sink in sinks:
                logger.info(f"Analyzing call SINK with name 'createQuery()' at line {sink.line} in {sink.file}")
                dftp, targetDFGName = Gremlin().findASTNodeInDFG(sink.sharedId)
                if cpg.checkReachability(dfsp, dftp, sourceDFGName):
                    logger.info("Reachability has been found")
                    # subgraph = cpg.getInitialCFSubgraph(dfsp)
                    # if subgraph is not None:
                    #     cfSource = None
                    #     cfTarget = None
                    #     for CFG in Database().getAllCFGs().values():
                    #         if CFG.getNodeByID(dfsp.sharedId):
                    #             cfSource = CFG.getNodeByID(dfsp.sharedId)
                    #         if CFG.getNodeByID(dftp.sharedId):
                    #             cfTarget = CFG.getNodeByID(dftp.sharedId)

                        # engine = CFEngine(subgraph, "userInput()", sourceType, sinkArgType, cfSource, cfTarget)
                        # logger.info("Run result: " + str(engine.initPartialRun(subgraph, '"Hello"')))
                else:
                    logger.info("No reachability")
                logger.info("=========================================================================")

    elif sys.argv[1] == "callgraph":
        db = Database()
        db.clear(DBCollections.CallGraph)
        javaClasses = db.getAllJavaClasses()
        for jc in javaClasses.values():
            packageName = jc.package
            className = jc.name
            for method in jc.methods:
                methodQN = f"{packageName}.{className}.{method.name}"
                print(f"Searching for callees for {methodQN} ...")
                gResp = Gremlin().g.V().hasLabel("ASTNode").has("kind", "CLASS").where(
                        __.out().has("kind", "NAME").has("code", className)
                    )\
                    .out().has("kind", "METHOD").where(
                        __.out().has("kind", "NAME").has("code", method.name)
                    ).repeat(__.out()).emit().has("kind", "CALL").out().has("kind", "NAME").values("code").toList()
                if len(gResp) > 0:
                    Database().putInCallGraph(methodQN, gResp)
        db.commit()


    elif sys.argv[1] == "dir_populate":
        Database().clear()

        # Сначала собираем инфу обо всех классах и их методах. Она нам понадобится для межпроцедурных потоков данных
        logger.info("Obtaining Java classes info...")
        for dirname, dirnames, filenames in os.walk(Config.TARGET_DIR):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                JavaClassExtractor.extractInfo(filePath)
        logger.info("Done")

        logger.info("Building graphs...")
        for dirname, dirnames, filenames in os.walk(Config.TARGET_DIR):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                logger.info("Handling: " + filePath)
                ast = ASTBuilder.build(filePath)
                ast.exportGraphML(filename)
                cfgs = CFGBuilder.build(filePath)
                for methodName, CFG in cfgs.items():
                    CFG.exportGraphML(filename=methodName)
                dfgs = DFGBuilder.build(filePath, ast)
        logger.info("Done")

    elif sys.argv[1] == "dir_plots":
        Database().clear()
        projDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "dvja")

        # Сначала собираем инфу обо всех классах и их методах. Она нам понадобится для межпроцедурных потоков данных
        logger.info("Obtaining Java classes info...")
        for dirname, dirnames, filenames in os.walk(projDir):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                JavaClassExtractor.extractInfo(filePath)
        logger.info("Done")

        logger.info("Building graphs...")
        for dirname, dirnames, filenames in os.walk(projDir):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                logger.info("Handling: " + filePath)
                logger.info("Building AST...")
                ast = ASTBuilder.build(filePath)
                ast.exportSVG(filename)
                logger.info("Building CFGs...")
                cfgs = CFGBuilder.build(filePath)
                for methodName, CFG in cfgs.items():
                    CFG.exportSVG(filename=methodName)
                logger.info("Building DFGs...")
                dfgs = DFGBuilder.build(filePath, ast)
                for methodName, DFG in dfgs.items():
                    DFG.exportSVG(filename=methodName)
        Database().commit()
        logger.info("Done")

    elif sys.argv[1] == "dir_ast_plots":
        Database().clear(DBCollections.ASTs)

        logger.info("Building graphs...")
        for dirname, dirnames, filenames in os.walk(Config.TARGET_DIR):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                logger.info("Handling: " + filePath)
                logger.info("Building AST...")
                ast = ASTBuilder.build(filePath)
                packageName = ast.getProperty("package")
                baseName = os.path.splitext(filename)[0]
                ast.exportNew(f"{packageName}.{baseName}")
        logger.info("Done")
        logger.info("Dumping database...")
        Database().commit()

    elif sys.argv[1] == "dir_cfg_plots":
        Database().clear(DBCollections.CFGs)

        logger.info("Building graphs...")
        for dirname, dirnames, filenames in os.walk(Config.TARGET_DIR):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                logger.info("Handling: " + filePath)
                logger.info("Building CFGs...")
                cfgs = CFGBuilder.build(filePath)
                for qn, CFG in cfgs.items():
                    CFG.exportNew(filename=qn)
        logger.info("Done")
        logger.info("Dumping database...")
        Database().commit()

    elif sys.argv[1] == "dir_java_classes_plots":
        Database().clear(DBCollections.JavaClasses)

        logger.info("Obtaining Java classes info...")
        for dirname, dirnames, filenames in os.walk(Config.TARGET_DIR):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                logger.info("Handling: " + filePath)
                JavaClassExtractor.extractInfo(filePath)
        logger.info("Done")
        logger.info("Dumping database...")
        Database().commit()

    elif sys.argv[1] == "dir_dfg_plots":
        Database().clear(DBCollections.DFGs)

        logger.info("Building graphs...")
        for dirname, dirnames, filenames in os.walk(Config.TARGET_DIR):
            for filename in filenames:
                if not filename.endswith(".java"):
                    continue
                filePath = os.path.join(dirname, filename)
                logger.info("Handling: " + filePath)
                logger.info("Building DFGs...")
                cfgs = Database().getCFGsByFilePath(filePath)

                # Если нет функций и их CFG, то следовательно нет и DFG
                if len(cfgs) == 0:
                    continue
                    
                ast = Database().getASTByFilePath(filePath)
                dfgs = DFGBuilder.build(filePath, ast)
                for qn, DFG in dfgs.items():
                    DFG.exportNew(filename=qn)
        dfgs = Database().getAllDFGs()
        DFGBuilder.addIPDataFlows(dfgs)
        logger.info("Done")
        logger.info("Dumping database...")
        Database().commit()

    elif sys.argv[1] == "orientdb_populate":
        OrientDB().populate()

    elif sys.argv[1] == "orientdb_populate_ast":
        OrientDB().populateASTs()

    elif sys.argv[1] == "orientdb_populate_cfg":
        OrientDB().populateCFGs()

    elif sys.argv[1] == "orientdb_populate_dfg":
        OrientDB().populateDFGs()

    elif sys.argv[1] == "orientdb_clear":
        OrientDB().clear()

    elif sys.argv[1] == "clear":
        for filename in os.listdir(Config.AST_PLOTS_DIR):
            os.remove(os.path.join(Config.AST_PLOTS_DIR, filename))
        for filename in os.listdir(Config.CFG_PLOTS_DIR):
            os.remove(os.path.join(Config.CFG_PLOTS_DIR, filename))
        for filename in os.listdir(Config.DFG_PLOTS_DIR):
            os.remove(os.path.join(Config.DFG_PLOTS_DIR, filename))
        for filename in os.listdir(Config.AST_GRAPHML_DIR):
            os.remove(os.path.join(Config.AST_GRAPHML_DIR, filename))
        for filename in os.listdir(Config.CFG_GRAPHML_DIR):
            os.remove(os.path.join(Config.CFG_GRAPHML_DIR, filename))
        for filename in os.listdir(Config.DFG_GRAPHML_DIR):
            os.remove(os.path.join(Config.DFG_GRAPHML_DIR, filename))
        os.remove(Config.CPG_DB)


