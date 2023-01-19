import os.path
from flask_cors import CORS
from flask import Flask, render_template, send_from_directory, send_file, Response, make_response, url_for, abort
import json

from werkzeug.utils import redirect

from config import Config
from db import Database
from schemas import JavaClassSchema, JavaMethodSchema

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return redirect(url_for("showJavaClasses"))


@app.route('/java-classes')
def showJavaClasses():
    with open(app.config["DB"], "r") as f:
        javaClassesJson = json.load(f)["javaClasses"]

    javaClasses = dict()
    for qn, jc in javaClassesJson.items():
        javaClasses[qn] = JavaClassSchema().load(jc)
    return render_template("java-classes.html", javaClasses=javaClasses)




@app.route("/methods/<string:qualifiedClassName>")
def showMethods(qualifiedClassName):
    with open(app.config["DB"], "r") as f:
        javaClassesJson = json.load(f)["javaClasses"]

    javaClass = javaClassesJson[qualifiedClassName]
    methods = javaClass["methods"]
    methods = JavaMethodSchema(many=True).load(methods)

    return render_template("methods.html", methods=methods, javaClass=javaClass)


@app.route("/ast/<string:qualifiedClassName>")
def showAST(qualifiedClassName):
    with open(app.config["DB"], "r") as f:
        javaClassesJson = json.load(f)["javaClasses"]

    javaClass = JavaClassSchema().load(javaClassesJson[qualifiedClassName])
    filename = os.path.splitext(os.path.basename(javaClass.filePath))[0]

    plotFilename = f"ast-{javaClass.package}.{filename}.svg"
    return render_template("show-plot.html", plotFilename=plotFilename, kind="ast",
                           qn=qualifiedClassName, qnForNodeInfo=qualifiedClassName)


@app.route("/cfg/<string:qualifiedMethodName>")
def showCFG(qualifiedMethodName):
    plotFilename = f"cfg-{qualifiedMethodName}.svg"
    className = '.'.join(qualifiedMethodName.split('.')[:-1])
    return render_template("show-plot.html",
                           plotFilename=plotFilename, kind="cfg",
                           qn=className, qnForNodeInfo=qualifiedMethodName)


@app.route("/dfg/<string:qualifiedMethodName>")
def showDFG(qualifiedMethodName):
    plotFilename = f"dfg-{qualifiedMethodName}.svg"
    className = '.'.join(qualifiedMethodName.split('.')[:-1])
    return render_template("show-plot.html",
                           plotFilename=plotFilename, kind="dfg",
                           qn=className, qnForNodeInfo=qualifiedMethodName)


@app.route("/plot/<string:kind>/<string:filename>")
def getPlot(kind, filename):
    if kind == "ast":
        return send_from_directory(os.path.join(os.getcwd(), Config.AST_PLOTS_DIR), filename)
    elif kind == "cfg":
        return send_from_directory(os.path.join(os.getcwd(), Config.CFG_PLOTS_DIR), filename)
    elif kind == "dfg":
        return send_from_directory(os.path.join(os.getcwd(), Config.DFG_PLOTS_DIR), filename)
    else:
        return abort(404)


@app.route("/source-code/<string:qualifiedClassName>")
def getSourceCode(qualifiedClassName):
    with open(app.config["DB"], "r") as f:
        javaClassesJson = json.load(f)["javaClasses"]

    javaClass = javaClassesJson.get(qualifiedClassName)
    filePath = javaClass["filePath"]

    with open(filePath) as f:
        code = f.read()

    return render_template("show-source-code.html", filePath=filePath, code=code)


@app.route("/node/ast/<string:fileQN>/<int:nodeId>")
def getAstNodeInfo(fileQN, nodeId):
    with open(app.config["DB"]) as f:
        ASTsJson = json.load(f)["asts"]

    AST = ASTsJson.get(fileQN)
    if AST is None:
        return abort(404)

    for node in AST["nodes"]:
        if node["Id"] == nodeId:
            return node

    return abort(404)


@app.route("/node/cfg/<string:methodQn>/<int:nodeId>")
def getCfgNodeInfo(methodQn, nodeId):
    with open(app.config["DB"]) as f:
        CFGsJson = json.load(f)["cfgs"]

    CFG = CFGsJson.get(methodQn)
    if CFG is None:
        return abort(404)

    for node in CFG["nodes"]:
        if node["Id"] == nodeId:
            return node

    return abort(404)


@app.route("/node/dfg/<string:methodQn>/<int:nodeId>")
def getDfgNodeInfo(methodQn, nodeId):
    with open(app.config["DB"]) as f:
        DFGsJson = json.load(f)["dfgs"]

    DFG = DFGsJson.get(methodQn)
    if DFG is None:
        return abort(404)

    for node in DFG["nodes"]:
        if node["Id"] == nodeId:
            return node

    return abort(404)


def runWebApp(projectConfig):
    app.config["DB"] = projectConfig["DB"]
    app.run()


if __name__ == "__main__":
    app.run()
