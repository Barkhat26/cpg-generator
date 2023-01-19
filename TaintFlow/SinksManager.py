from GremlinDriver import Gremlin
from TaintFlow.sinkPatterns import findCreateQuery, findExecuteQuery, findSinkByMethodQNCall, findSinkInAssingments, \
    findSaveMethodCalls, findExec
from db import Database
from utils import hasSuperClass


class SinksManager:
    def __init__(self, projectConfig):
        self.projectConfig = projectConfig
        self.gremlin = Gremlin(projectConfig)

    def getSinks(self):
        astSinks = []
        if self.projectConfig["web-framework"] == "Struts2":
            astSinks = findCreateQuery(self.gremlin)

            db = Database(self.projectConfig)
            for classQN, jc in db.getAllJavaClasses().items():
                if hasSuperClass(classQN, "ActionSupport", db):
                    for field in jc.fieldList:
                        setter = "set" + field.name[0].upper() + field.name[1:]
                        setterQN = f"{classQN}.{setter}"
                        astSinks.extend(findSinkByMethodQNCall(setterQN, self.gremlin))
                        astSinks.extend(findSinkInAssingments(field.name, self.gremlin))

            astSinks.extend(findSaveMethodCalls(self.gremlin))
            astSinks.extend(findExec(self.gremlin))

        elif self.projectConfig["web-framework"] == "SpringMVC":
            astSinks = findExecuteQuery(self.gremlin)

        seen_sharedIds = set()
        new_list = []
        for obj in astSinks:
            if obj.sharedId not in seen_sharedIds:
                new_list.append(obj)
                seen_sharedIds.add(obj.sharedId)

        return new_list
