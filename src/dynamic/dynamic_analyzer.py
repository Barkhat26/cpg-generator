from typing import Optional

from web_driver import WebDriver
from checkpoint_manager import CheckpointManager
from instrument_tool import InstrumentTool
from attacker import Attacker
from taint_flow.endpoint_extractors.base_endpoint_extractor import BaseEndpointExtractor
from taint_flow.attack_endpoint_extractors.base_attack_endpoint_extractor import BaseAttackEndpointExtractor


class DynamicAnalyzer:
    def __init__(self, project_config):
        self.projectConfig = project_config
        self.endpointExtractor: Optional[BaseEndpointExtractor] = None
        self.attackEndpointExtractor: Optional[BaseAttackEndpointExtractor] = None
        self.webDriver: Optional[WebDriver] = None

    def setEndpointExtractor(self, endpoint_extractor: BaseEndpointExtractor):
        self.endpointExtractor = endpoint_extractor

    def setAttackEndpointExtractor(self, attack_endpoint_extractor: BaseAttackEndpointExtractor):
        self.attackEndpointExtractor = attack_endpoint_extractor

    def setWebDriver(self, web_driver: WebDriver):
        self.webDriver = web_driver

    def run(self):
        self.checkReadiness()

        # First
        self.endpointExtractor.extractEndpoints()
        self.endpointExtractor.dump()
        self.attackEndpointExtractor.extractEndpoints()
        self.attackEndpointExtractor.dump()

        # Second
        checkpoint_manager = CheckpointManager(project_config=self.projectConfig)
        checkpoint_manager.prepare()
        instrument_tool = InstrumentTool(self.projectConfig, checkpoint_manager)
        instrument_tool.instrument()
        input("Run an application. Enter an any key while it is ready up...")

        # Third
        self.webDriver.authenticate()
        self.webDriver.prepare()
        attacker = Attacker(self.webDriver, checkpoint_manager, self.projectConfig)
        attacker.attack()
        input("Stop an application. Enter an any key while it is ready up...")

        # Fourth
        instrument_tool.revert()

    def checkReadiness(self):
        if self.endpointExtractor is None:
            print("Not defined an EndpointExtractor. Use setEndpointExtractor method")
            exit(1)

        if self.attackEndpointExtractor is None:
            print("Not defined an AttackEndpointExtractor. Use setAttackEndpointExtractor method")
            exit(1)

        if self.webDriver is None:
            print("Not defined an WebDriver. Use setWebDriver method")
            exit(1)