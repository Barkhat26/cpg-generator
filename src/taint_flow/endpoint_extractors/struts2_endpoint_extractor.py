from config import Config
import os.path
from bs4 import BeautifulSoup as bs
import json
import re
from dataclasses import dataclass

from taint_flow.endpoint_extractors.base_endpoint_extractor import BaseEndpointExtractor


@dataclass
class StrutsAction:
    class_: str
    method: str


@dataclass
class StrutsFormData:
    action: str
    names: list[str]


class Struts2EndpointExtractor(BaseEndpointExtractor):
    def __init__(self, jsp_files_dir: str, struts_xml_file: str):
        self.jsp_files_dir = jsp_files_dir
        self.struts_xml_file = struts_xml_file
        self.viewData: dict[str, StrutsFormData] = {}
        self.routeData: dict[str, StrutsAction] = {}

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
        self._extractViewData()
        self._extractRouteData()

    def _extractViewData(self):
        for dirname, dirnames, filenames in os.walk(self.jsp_files_dir):
            for filename in filenames:
                if not filename.endswith(".jsp"):
                    continue

                file_path = os.path.join(dirname, filename)
                with open(file_path) as f:
                    jsp_content = f.read()

                rel_path = os.path.relpath(file_path, self.jsp_files_dir)

                if form_data := self._get_form_data(jsp_content):
                    self.viewData[rel_path] = form_data


    def _extractRouteData(self):
        with open(self.struts_xml_file) as f:
            struts_xml_content = f.read()

        soup = bs(struts_xml_content, "lxml")

        for package in soup.find_all("package"):
            package_name = package["name"]

            for action in package.find_all("action"):
                if package_name == "default":
                    name = action["name"]
                else:
                    name = package_name + "." + action["name"]

                self.routeData[name] = StrutsAction(
                    class_=action.get("class", [None])[0],
                    method=action.get("method")
                )

        includes = soup.find_all("include")

        if len(includes) > 0:
            for include in includes:
                if not os.path.exists(include["file"]):
                    file_path = os.path.join(os.path.dirname(self.struts_xml_file), include["file"])
                else:
                    file_path = include["file"]

                with open(file_path) as f:
                    include_xml_content = f.read()

                soup = bs(include_xml_content, "lxml")

                for package in soup.find_all("package"):
                    package_name = package["name"]

                    for action in package.find_all("action"):
                        if package_name == "default":
                            name = action["name"]
                        else:
                            name = package_name + "." + action["name"]

                        self.routeData[name] = StrutsAction(
                            class_=action.get("class", [None])[0],
                            method=action.get("method")
                        )

    def _get_form_data(self, jsp_content: str) -> StrutsFormData | None:
        found_forms = re.findall(r"<s:form [^>]*>.*</s:form>", jsp_content, re.DOTALL)
        result = dict()

        for ff in found_forms:
            action = re.findall(r'<s:form action="(?P<action>[^"]*)"', ff, re.DOTALL)[0]
            result["action"] = action

            found_text_fields = re.findall(r"<s:textfield\s+[^>]*\/>", ff, re.DOTALL)
            result["names"] = []
            for ftf in found_text_fields:
                result["names"].append(self._get_name_from_tag(ftf))

            found_passwords = re.findall(r"<s:password\s+[^>]*\/>", ff, re.DOTALL)
            for fp in found_passwords:
                result["names"].append(self._get_name_from_tag(fp))

            found_text_areas = re.findall(r"<s:textarea\s+[^>]*\/>", ff, re.DOTALL)
            for fta in found_text_areas:
                result["names"].append(self._get_name_from_tag(fta))

            found_hiddens = re.findall(r"<s:hidden\s+[^>]*\/>", ff, re.DOTALL)
            for fh in found_hiddens:
                result["names"].append(self._get_name_from_tag(fh))

        if not result:
            return None

        return StrutsFormData(
            action=result['action'],
            names=result['names']
        )

    @staticmethod
    def _get_name_from_tag(tag) -> str | None:
        for k, v in [attr_val.split("=") for attr_val in re.findall(r'(\w+="[^"]*")', tag)]:
            if k == "name":
                return v.replace('"', "")

        return None
