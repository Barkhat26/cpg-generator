from config import Config
import os.path
from bs4 import BeautifulSoup as bs
import json
from TaintFlow.EndpointExtractors.BaseEndpointExtractor import BaseEndpointExtractor


def isController(_javaClass):
    annotations = _javaClass["annotations"]
    for a in annotations:
        if a["name"] == "Controller" or a["name"] == "RestController":
            return True

    return False


def isRoute(_javaMethod):
    annotations = _javaMethod["annotations"]
    for a in annotations:
        if a["name"] in ("PostMapping", "GetMapping", "RequestMapping"):
            return True

    return False


def getRouteDataFromMethod(_javaMethod):
    annotations = _javaMethod["annotations"]
    for a in annotations:
        if a["name"] in ("PostMapping", "GetMapping", "RequestMapping"):
            requestParams = []
            for arg in _javaMethod["args"]:
                for argAnnotation in arg["annotations"]:
                    if argAnnotation["name"] == "RequestParam":
                        requestParams.append(arg["name"])
            return {
                "method": _javaMethod["name"],
                "route": a["values"][0],
                "params": requestParams
            }


def getViewDataFromForms(fileContent):
    soup = bs(fileContent, "html.parser")
    formsData = []
    for form in soup.find_all("form"):
        httpMethod = form["method"]
        action = form["action"]
        requestParams = []
        for inputTag in form.find_all("input"):
            requestParams.append(inputTag["name"])
        formsData.append({
            "action": action,
            "method": httpMethod,
            "params": requestParams
        })
    return formsData


class SpringMVCEndpointExtractor(BaseEndpointExtractor):
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.viewData = {}
        self.routeData = {}

    def getViewData(self):
        return self.viewData

    def getRouteData(self):
        return self.routeData

    def dump(self):
        with open(Config.VIEW_DATA_FILE, "w") as f:
            json.dump(self.viewData, f, indent=4)

        with open(Config.ROUTE_DATA_FILE, "w") as f:
            json.dump(self.routeData, f, indent=4)

    def extractEndpoints(self):
        self.extractViewData()
        self.extractRouteData()

    def extractViewData(self):
        totalViewData = []
        for dirname, dirnames, filenames in os.walk(self.projectConfig["VIEWS_DIR"]):
            for filename in filenames:
                if not filename.endswith(".html"):
                    continue

                filePath = os.path.join(dirname, filename)
                with open(filePath) as f:
                    viewContent = f.read()

                viewData = getViewDataFromForms(viewContent)
                totalViewData.extend(viewData)

        self.viewData = totalViewData

    def extractRouteData(self):
        with open(self.projectConfig["DB"]) as f:
            dbJson = json.load(f)

        javaClasses = dbJson["javaClasses"]

        totalRouteData = []
        for className, jc in javaClasses.items():
            if isController(jc):
                for method in jc["methods"]:
                    if isRoute(method):
                        routeData = getRouteDataFromMethod(method)
                        routeData["class"] = className
                        totalRouteData.append(routeData)
        self.routeData = totalRouteData
