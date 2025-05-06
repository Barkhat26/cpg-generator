import json

from taint_flow.attack_endpoint_extractors.base_attack_endpoint_extractor import BaseAttackEndpointExtractor
from config import Config

class Struts2AttackEndpointExtractor(BaseAttackEndpointExtractor):
    def __init__(self, project_config):
        self.projectConfig = project_config
        self.data = [{
            "vulnerability": "...",
            "uri": "/userSearch",
            "params": [
                "login"
            ],
            "sourceSharedId": "8a...",
            "sinkSharedId": "ca...",
            "sinkLine": "...",
            "sinkFile": "...",
            "sinkCode": "..."
        }]

    def extractEndpoints(self):
        ...

    def dump(self):
        with open(Config.ATTACK_ENDPOINTS_FILE, "w") as f:
            json.dump(self.data, f, indent=4)
