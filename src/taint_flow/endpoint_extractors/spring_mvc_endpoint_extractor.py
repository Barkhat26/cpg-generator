from dataclasses import dataclass
from config import Config
import os.path
from bs4 import BeautifulSoup as bs
import json

from java.java_structures import JavaClass, JavaMethod
from taint_flow.endpoint_extractors.base_endpoint_extractor import BaseEndpointExtractor

@dataclass
class FormData:
    action: str
    method: str
    params: list[str]

@dataclass
class RouteData:
    class_: str
    method: str
    params: list[str]
    route: str

class SpringMVCEndpointExtractor(BaseEndpointExtractor):
    def __init__(self, views_dir: str, java_classes: dict[str, JavaClass]):
        self.views_dir = views_dir
        self.java_classes = java_classes
        self.forms = []
        self.routes = []

    def dump(self):
        with open(Config.VIEW_DATA_FILE, "w") as f:
            json.dump(self.forms, f, indent=4)

        with open(Config.ROUTE_DATA_FILE, "w") as f:
            json.dump(self.routes, f, indent=4)

    def extractEndpoints(self):
        self.extractViewData()
        self.extractRouteData()

    def extractViewData(self):
        for dirname, dirnames, filenames in os.walk(self.views_dir):
            for filename in filenames:
                if not filename.endswith((".html", ".jsp")):
                    continue

                file_path = os.path.join(dirname, filename)
                with open(file_path) as f:
                    view_content = f.read()

                view_data = self.getViewDataFromForms(view_content)
                self.forms.extend(view_data)

    def extractRouteData(self):
        for className, jc in self.java_classes.items():
            if not self.isController(jc):
                continue

            for method in jc.methods:
                if not self.isRoute(method):
                    continue

                route_data = self.getRouteDataFromMethod(method, className)
                self.routes.append(route_data)

    @staticmethod
    def isController(java_class: JavaClass):
        for a in java_class.annotations:
            if a.name == "Controller" or a.name == "RestController":
                return True

        return False

    @staticmethod
    def isRoute(java_method):
        annotations = java_method.annotations
        for a in annotations:
            if a.name in ("PostMapping", "GetMapping", "RequestMapping"):
                return True

        return False

    @staticmethod
    def getRouteDataFromMethod(java_method: JavaMethod, class_name: str):
        for a in java_method.annotations:
            if a.name not in ("PostMapping", "GetMapping", "RequestMapping"):
                continue

            request_params = []
            for arg in java_method.args:
                for argAnnotation in arg.annotations:
                    if argAnnotation.name == "RequestParam":
                        request_params.append(arg.name)

            return RouteData(
                class_=class_name,
                method=java_method.name,
                route=a.values[0],
                params=request_params
            )

    @staticmethod
    def getViewDataFromForms(file_content: str) -> list[FormData]:
        soup = bs(file_content, "html.parser")
        forms_data_list: list[FormData] = []

        for form in soup.find_all("form"):
            http_method = form["method"]
            action = form["action"]
            request_params = []

            for inputTag in form.find_all("input"):
                request_params.append(inputTag["name"])

            forms_data_list.append(FormData(action, http_method, request_params))

        return forms_data_list
