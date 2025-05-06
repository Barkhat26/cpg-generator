import json

from config import Config
from dynamic.vulnerabilitykind import VulnerabilityKind
from web_driver import WebDriver
from checkpoint_manager import CheckpointManager
from checkers import checkers
from report import Report

payloads = {
    VulnerabilityKind.SQL: "\' or 1=1 -- sample",
    VulnerabilityKind.XSS: "some<script>alert(4);</script>",
    VulnerabilityKind.Command: "localhost; ls"
}


class Attacker:
    def __init__(self, web_driver: WebDriver, checkpoint_manager: CheckpointManager, project_config):
        self.checkpointManager = checkpoint_manager
        self.attackEndpoints = self._loadAttackEndpoints()
        self.webDriver = web_driver
        self.projectConfig = project_config
        self.report = Report()

    def attack(self):
        for attackEndpoint in self.attackEndpoints:
            vulnerability = VulnerabilityKind.from_str(attackEndpoint['vulnerability'])
            endpoint_uri = attackEndpoint["uri"]
            full_uri = f"{self.projectConfig['base_url']}{endpoint_uri}"
            print(f"Testing {endpoint_uri}...")

            for testParam in attackEndpoint["params"]:
                print(f'\tTesting parameter "{testParam}"...')
                # Safe-запрос
                # TODO: здесь можно оптимизировать, создав заранее словарь из "COMMON_PARAM_VALUE", и поверхностно копировать его, заменяя test-param
                payload = {param: "test" if param == testParam else "COMMON_PARAM_VALUE" for param in attackEndpoint["params"]}
                self.webDriver.post(full_uri, data=payload)

                # Фиксируем результаты safe-запроса
                checker = checkers[vulnerability]()
                checkpoint_value = self.checkpointManager.get_checkpoint_value(attackEndpoint["sinkSharedId"])
                checker.setSafeQuery(checkpoint_value)

                # Unsafe-запрос
                payload[testParam] = payloads[vulnerability]
                self.webDriver.post(full_uri, data=payload)

                # Достаем результаты unsafe-запроса
                checkpoint_value = self.checkpointManager.get_checkpoint_value(attackEndpoint["sinkSharedId"])

                # Сравниваем результаты safe- и unsafe-запроса
                if not checker.checkPotentialUnsafeQuery(checkpoint_value):
                    self.report.addRecord(attackEndpoint, testParam)
                    line = attackEndpoint['sinkLine']
                    file = attackEndpoint['sinkFile']
                    code = attackEndpoint['sinkCode']
                    shared_id = attackEndpoint['sinkSharedId']
                    print(f"Potential vulnerability ({vulnerability}) has been found!!!!! URI: {endpoint_uri}\n"
                        f"\tin file {file} at line {line} ({shared_id})\n"
                        f"\t{code}")
                print("----------------------------------------------------")

        self.report.dump()

    @staticmethod
    def _loadAttackEndpoints():
        with open(Config.ATTACK_ENDPOINTS_FILE) as f:
            return json.load(f)