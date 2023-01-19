from GremlinDriver import Gremlin
from TaintFlow.EndpointExtractors.SpringMVCEndpointExtractor import SpringMVCEndpointExtractor
from TaintFlow.sourcePatterns import findSourceForSpringMVC, findSourceByMethodQNCall, findSourceInParams
from db import Database
from utils import hasSuperClass


class SourcesManager:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.gremlin = Gremlin(projectConfig)

    def getSources(self):
        astSources = []
        if self.projectConfig["web-framework"] == "Struts2":
            db = Database(self.projectConfig)
            for classQN, jc in db.getAllJavaClasses().items():
                if hasSuperClass(classQN, "ActionSupport", db):
                    for field in jc.fieldList:
                        getter = "get" + field.name[0].upper() + field.name[1:]
                        getterQN = f"{classQN}.{getter}"
                        astSources.extend(findSourceByMethodQNCall(getterQN, self.gremlin))
                        astSources.extend(findSourceInParams(field.name, self.gremlin))

        elif self.projectConfig["web-framework"] == "SpringMVC":
            endpointExtractor = SpringMVCEndpointExtractor(self.projectConfig)
            endpointExtractor.extractRouteData()
            controllersData = endpointExtractor.getRouteData()

            for item in controllersData:
                astSources.extend(findSourceForSpringMVC(
                    classQN=item["class"],
                    methodName=item["method"],
                    params=item["params"],
                    gremlin=self.gremlin)
                )

        else:
            print("For web framework '%s' does not implement source search" % self.projectConfig["web-framework"])

        seen_sharedIds = set()
        new_list = []
        for obj in astSources:
            if obj.sharedId not in seen_sharedIds:
                new_list.append(obj)
                seen_sharedIds.add(obj.sharedId)

        return new_list
