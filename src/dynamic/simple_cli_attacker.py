import subprocess

from dynamic.checkers import CIChecker
from dynamic.checkpoint_manager import CheckpointManager
from taint_flow.taintflow import TaintFlow
from log import simple_cli_attacker_logger as logger


class SimpleCLIAttacker:
    def __init__(self, checkpoint_manager: CheckpointManager, args: list[str]):
        self.args = args
        self.checkpoint_manager = checkpoint_manager

    def attack(self) -> bool:
        attack_is_successful = False
        checker = CIChecker()

        for taint_flow in self.checkpoint_manager.taint_flows:
            payload = 'dir'
            self._start_process_and_pass_payload(payload)
            checkpoint_value = self.checkpoint_manager.get_checkpoint_value(taint_flow.sink.shared_id)
            checker.setSafeQuery(checkpoint_value)

            payload = 'cmd /c dir && whoami'
            self._start_process_and_pass_payload(payload)
            checkpoint_value = self.checkpoint_manager.get_checkpoint_value(taint_flow.sink.shared_id)

            if not checker.checkPotentialUnsafeQuery(checkpoint_value):
                line = taint_flow.sink.line
                file = taint_flow.sink.file
                code = taint_flow.sink.code
                shared_id = taint_flow.sink.shared_id
                logger.info(f"Potential vulnerability ({taint_flow.vulnerability}) has been found!!!!!\n"
                      f"\tin file {file} at line {line} ({shared_id})\n"
                      f"\t{code}")
                attack_is_successful = True

        return attack_is_successful

    def _start_process_and_pass_payload(self, payload: str):
        # Команда запуска программы
        proc = subprocess.Popen(
            self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # работает как universal_newlines=True, позволяет писать строки
        )

        # Отправка ввода и получение вывода
        output, errors = proc.communicate(input=f'{payload}\n')

        logger.debug("Output:")
        logger.debug(output)

        logger.debug("Errors:")
        logger.debug(errors)



