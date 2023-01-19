from dynamic_analyzer.config import Config
import os.path
from bs4 import BeautifulSoup as bs
import json
import re

from dynamic_analyzer.EndpointExtractors.BaseEndpointExtractor import BaseEndpointExtractor


def getNameFromTag(tag):
    for k, v in [attr_val.split("=") for attr_val in re.findall(r'(\w+="[^"]*")', tag)]:
        if k == "name":
            return v.replace('"', "")


def getFormData(_jspContent):
    foundForms = re.findall(r"<s:form [^>]*>.*</s:form>", _jspContent, re.DOTALL)
    result = dict()

    for ff in foundForms:
        action = re.findall(r'<s:form action="(?P<action>[^"]*)"', ff, re.DOTALL)[0]
        result["action"] = action

        foundTextFields = re.findall(r"<s:textfield\s+[^>]*\/>", ff, re.DOTALL)
        result["names"] = []
        for ftf in foundTextFields:
            result["names"].append(getNameFromTag(ftf))

        foundPasswords = re.findall(r"<s:password\s+[^>]*\/>", ff, re.DOTALL)
        for fp in foundPasswords:
            result["names"].append(getNameFromTag(fp))

        foundTextAreas = re.findall(r"<s:textarea\s+[^>]*\/>", ff, re.DOTALL)
        for fta in foundTextAreas:
            result["names"].append(getNameFromTag(fta))

        foundHiddens = re.findall(r"<s:hidden\s+[^>]*\/>", ff, re.DOTALL)
        for fh in foundHiddens:
            result["names"].append(getNameFromTag(fh))

    return result


class Struts2EndpointExtractor(BaseEndpointExtractor):
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
        globalResult = dict()
        JSPFilesDir = self.projectConfig["JSPFilesDir"]
        for dirname, dirnames, filenames in os.walk(JSPFilesDir):
            for filename in filenames:
                if not filename.endswith(".jsp"):
                    continue

                filePath = os.path.join(dirname, filename)
                with open(filePath) as f:
                    jspContent = f.read()

                globalResult[os.path.relpath(filePath, JSPFilesDir)] = getFormData(jspContent)

        self.viewData = globalResult

    def extractRouteData(self):
        with open(self.projectConfig["STRUTS_XML"]) as f:
            strutsXmlContent = f.read()

        actions = dict()
        soup = bs(strutsXmlContent, "lxml")
        for package in soup.find_all("package"):
            packageName = package["name"]
            for action in package.find_all("action"):
                if packageName == "default":
                    name = action["name"]
                else:
                    name = packageName + "." + action["name"]
                actions[name] = {
                    "class": action.get("class", [None])[0],
                    "method": action.get("method")
                }

        includes = soup.find_all("include")
        if len(includes) > 0:
            for include in includes:
                if not os.path.exists(include["file"]):
                    filePath = os.path.join(os.path.dirname(self.projectConfig["STRUTS_XML"]), include["file"])
                else:
                    filePath = include["file"]
                with open(filePath) as f:
                    includeXmlContent = f.read()
                soup = bs(includeXmlContent, "lxml")
                for package in soup.find_all("package"):
                    packageName = package["name"]
                    for action in package.find_all("action"):
                        if packageName == "default":
                            name = action["name"]
                        else:
                            name = packageName + "." + action["name"]
                        actions[name] = {
                            "class": action.get("class", [None])[0],
                            "method": action.get("method")
                        }

        self.routeData = actions
