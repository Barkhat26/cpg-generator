import os.path


class Config:
    TEMPLATE_PROJECT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "template-config.json")
    PROJECT_CONFIG_FILENAME = "config.json"
    PLOTS_DIR = "plots"
    AST_PLOTS_DIR = os.path.join(PLOTS_DIR, "AST")
    CFG_PLOTS_DIR = os.path.join(PLOTS_DIR, "CFG")
    DFG_PLOTS_DIR = os.path.join(PLOTS_DIR, "DFG")

    VIEW_DATA_FILE = "viewData.json"
    ROUTE_DATA_FILE = "routeData.json"
