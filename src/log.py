import logging


class LoggerFactory:
    def __init__(self):
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")

        self.handler = logging.StreamHandler()
        self.handler.setFormatter(formatter)

    def init_module_logger(self, name: str, log_level=logging.NOTSET):
        module_logger = logging.getLogger(name)
        module_logger.setLevel(log_level)
        module_logger.addHandler(self.handler)
        return module_logger


factory = LoggerFactory()
general_logger             = factory.init_module_logger("general")
ast_builder_logger         = factory.init_module_logger("ast_builder")
ast_visitor_logger         = factory.init_module_logger("ast_visitor")
cfg_builder_logger         = factory.init_module_logger("cfg_builder")
cfg_visitor_logger         = factory.init_module_logger("cfg_visitor")
dfg_builder_logger         = factory.init_module_logger("dfg_builder")
dfg_visitor_logger         = factory.init_module_logger("dfg_visitor")
taint_flow_analyzer_logger = factory.init_module_logger("taint_flow_analyzer")
simple_cli_attacker_logger = factory.init_module_logger("simple_cli_attacker")


def set_global_log_level(log_level):
    general_logger.setLevel(log_level)
    ast_builder_logger.setLevel(log_level)
    ast_visitor_logger.setLevel(log_level)
    cfg_builder_logger.setLevel(log_level)
    cfg_visitor_logger.setLevel(log_level)
    dfg_builder_logger.setLevel(log_level)
    dfg_visitor_logger.setLevel(log_level)
    taint_flow_analyzer_logger.setLevel(log_level)
    simple_cli_attacker_logger.setLevel(log_level)
