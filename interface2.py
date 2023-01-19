import json
import os
import sys

from ASTBuilder import ASTBuilder
from CFGBuilder import CFGBuilder
from DFGBuilder import DFGBuilder
from GremlinDriver import Gremlin
from gremlin_python.process.graph_traversal import __
from JavaClassExtractor import JavaClassExtractor
from OrientDBDriver import OrientDB
from TaintFlow.SinksManager import SinksManager
from TaintFlow.SourcesManager import SourcesManager
from TaintFlow.utils import checkDFReachability, deleteDuplicateTaintFlows
from config import Config
from db import Database, DBCollections
from web.app import runWebApp


def runJClassesExtracting(projectConfig):
    db = Database(projectConfig)
    db.clear(DBCollections.JavaClasses)
    print("Obtaining Java classes info...")
    for dirname, dirnames, filenames in os.walk(projectConfig["target-dir"]):
        for filename in filenames:
            if not filename.endswith(".java"):
                continue
            filePath = os.path.join(dirname, filename)
            print("Handling: " + filePath)
            javaClassExtractor = JavaClassExtractor(projectConfig)
            javaClassExtractor.extractInfo(filePath)
            javaClassExtractor.dump()

    print("Done")
    print("Dumping database...")
    db.commit()


def runASTBuilding(projectConfig):
    db = Database(projectConfig)
    db.clear(DBCollections.ASTs)
    print("Building graphs...")
    for dirname, dirnames, filenames in os.walk(projectConfig["target-dir"]):
        for filename in filenames:
            if not filename.endswith(".java"):
                continue
            filePath = os.path.join(dirname, filename)
            print("Handling: " + filePath)
            print("Building AST...")
            astBuilder = ASTBuilder(projectConfig)
            astBuilder.build(filePath)
            astBuilder.dump()
            ast = astBuilder.getAST()
            packageName = ast.getProperty("package")
            baseName = os.path.splitext(filename)[0]
            ast.exportNew(f"{packageName}.{baseName}")
    print("Done")
    print("Dumping database...")
    db.commit()
    OrientDB(projectConfig).populateASTs()


def runCFGBuilding(projectConfig):
    db = Database(projectConfig)
    db.clear(DBCollections.CFGs)
    print("Building graphs...")
    for dirname, dirnames, filenames in os.walk(projectConfig["target-dir"]):
        for filename in filenames:
            if not filename.endswith(".java"):
                continue
            filePath = os.path.join(dirname, filename)
            print("Handling: " + filePath)
            print("Building CFGs...")
            cfgBuilder = CFGBuilder(projectConfig)
            cfgBuilder.build(filePath)
            cfgBuilder.dump()
            cfgs = cfgBuilder.getCFGs()
            for qn, CFG in cfgs.items():
                CFG.exportNew(filename=qn)
    print("Done")
    print("Dumping database...")
    db.commit()
    OrientDB(projectConfig).populateCFGs()


def runDFGBuilding(projectConfig):
    db = Database(projectConfig)
    db.clear(DBCollections.DFGs)
    print("Building graphs...")
    for dirname, dirnames, filenames in os.walk(projectConfig["target-dir"]):
        for filename in filenames:
            if not filename.endswith(".java"):
                continue
            filePath = os.path.join(dirname, filename)
            print("Handling: " + filePath)
            print("Building DFGs...")
            cfgs = db.getCFGsByFilePath(filePath)

            # Если нет функций и их CFG, то следовательно нет и DFG
            if len(cfgs) == 0:
                continue

            ast = db.getASTByFilePath(filePath)
            dfgBuilder = DFGBuilder(projectConfig)
            dfgBuilder.build(filePath, ast)
            dfgBuilder.dump()
            dfgs = dfgBuilder.getDFGs()
            for qn, DFG in dfgs.items():
                DFG.exportNew(filename=qn)
    dfgs = db.getAllDFGs()
    DFGBuilder.addIPDataFlows(dfgs, projectConfig)
    print("Done")
    print("Dumping database...")
    db.commit()
    OrientDB(projectConfig).populateDFGs()


def runTaintFlowAnalysis(projectConfig):
    astSources = SourcesManager(projectConfig).getSources()
    astSinks = SinksManager(projectConfig).getSinks()

    print(f"Found {len(astSources)} sources")
    if len(astSources) == 0:
        return

    print(f"Found {len(astSinks)} sinks")
    if len(astSinks) == 0:
        return

    gremlin = Gremlin(projectConfig)
    db = Database(projectConfig)
    db.clear(DBCollections.TaintFlows)

    taintFlows = []
    for astSink in astSinks:
        print(astSink.getOptionalProperty("sinkText") + " in file " + astSink.getFile() + " at line " + str(
            astSink.getLineOfCode()) + " (sharedId: " + astSink.getSharedId() + ")")
        dftp, targetDFGName = gremlin.findASTNodeInDFG(astSink.sharedId)
        print(f" DFG-node sharedId: {dftp.getSharedId()}")

        if astSink.getOptionalProperty("args"):
            dftp.setOptionalProperty("checkpoint", astSink.getOptionalProperty("args")[0])
        elif astSink.getOptionalProperty("assignmentExpression"):
            dftp.setOptionalProperty("checkpoint", astSink.getOptionalProperty("assignmentExpression"))

        for astSource in astSources:
            print("\t" + astSource.getOptionalProperty(
                "sourceText") + " in file " + astSource.getFile() + " at line " + str(
                astSource.getLineOfCode()) + " (sharedId: " + astSource.getSharedId() + ")")
            dfsp, sourceDFGName = gremlin.findASTNodeInDFG(astSource.sharedId)
            print(f"\t\tDFG-node sharedId: {dfsp.getSharedId()}")
            if checkDFReachability(gremlin, dfsp.getSharedId(), dftp.getSharedId()):
                taintFlows.append(dict(
                    source=dfsp, sink=dftp, vulnerability=astSink.getOptionalProperty("vulnerability"))
                )

    taintFlows = deleteDuplicateTaintFlows(taintFlows)
    db.setAllTaintFlows(taintFlows)
    print("Dumping to database...")
    db.commit()

def runCallgraphAnalysis(projectConfig):
    db = Database(projectConfig)
    db.clear(DBCollections.CallGraph)
    gremlin = Gremlin(projectConfig)
    javaClasses = db.getAllJavaClasses()
    for jc in javaClasses.values():
        packageName = jc.package
        className = jc.name
        for method in jc.methods:
            methodQN = f"{packageName}.{className}.{method.name}"
            print(f"Searching for callees for {methodQN} ...")
            gResp = gremlin.g.V().hasLabel("ASTNode").has("kind", "CLASS").where(
                __.out().has("kind", "NAME").has("code", className)
            ) \
                .out().has("kind", "METHOD").where(
                __.out().has("kind", "NAME").has("code", method.name)
            ).repeat(__.out()).emit().has("kind", "CALL").out().has("kind", "NAME").values("code").toList()
            if len(gResp) > 0:
                db.putInCallGraph(methodQN, gResp)
    db.commit()


def main():
    if len(sys.argv) < 2:
        print("Usage: python %s <command> [options]" % sys.argv[0])
        return

    command = sys.argv[1]
    if command == "init":
        if len(sys.argv) < 3:
            print("Usage: python %s init <project-name>" % sys.argv[0])
            return

        projectName = sys.argv[2]
        print(f"Creating a project with name '{projectName}'...")

        if os.path.exists(projectName):
            print(f"Directory with name '{projectName}' is existed")
            return

        os.mkdir(projectName)
        os.chdir(projectName)
        with open(Config.TEMPLATE_PROJECT_CONFIG) as f:
            projectConfigJson = json.load(f)
        projectConfigJson["name"] = projectName
        projectConfigJson["DB"] = f"{projectName}.db"
        projectConfigJson["orientdb-name"] = projectName
        with open(Config.PROJECT_CONFIG_FILENAME, "w") as f:
            json.dump(projectConfigJson, f, indent=4)
    elif command == "run-static":
        with open(Config.PROJECT_CONFIG_FILENAME) as f:
            projectConfig = json.load(f)

        subcommand = sys.argv[2]
        if subcommand == "all":
            runJClassesExtracting(projectConfig)
            runASTBuilding(projectConfig)
            runCFGBuilding(projectConfig)
            runDFGBuilding(projectConfig)
            runTaintFlowAnalysis(projectConfig)
            runCallgraphAnalysis(projectConfig)
        elif subcommand == "classes":
            runJClassesExtracting(projectConfig)
        elif subcommand == "ast":
            runASTBuilding(projectConfig)
        elif subcommand == "cfg":
            runCFGBuilding(projectConfig)
        elif subcommand == "dfg":
            runDFGBuilding(projectConfig)
        elif subcommand == "taint":
            runTaintFlowAnalysis(projectConfig)
        elif subcommand == "callgraph":
            runCallgraphAnalysis(projectConfig)

    elif command == "web":
        with open(Config.PROJECT_CONFIG_FILENAME) as f:
            projectConfig = json.load(f)

        runWebApp(projectConfig)


if __name__ == "__main__":
    main()
