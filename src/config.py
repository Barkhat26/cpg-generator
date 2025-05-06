import os.path
from pathlib import Path


class Config:
    TEMPLATE_PROJECT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "template-config.json")
    PROJECT_CONFIG_FILENAME = "config.json"
    PLOTS_DIR = "plots"
    AST_PLOTS_DIR = os.path.join(PLOTS_DIR, "AST")
    CFG_PLOTS_DIR = os.path.join(PLOTS_DIR, "CFG")
    DFG_PLOTS_DIR = os.path.join(PLOTS_DIR, "DFG")

    VIEW_DATA_FILE = "viewData.json"
    ROUTE_DATA_FILE = "routeData.json"
    ATTACK_ENDPOINTS_FILE = "attackData.json"

    APP_DATA_DIR = Path(os.environ['LOCALAPPDATA']) / "cpganalyzer"
    DEFAULT_PLOTS_DIR = APP_DATA_DIR / "plots"
    DEFAULT_DB_DIR = APP_DATA_DIR / "db"
    DEFAULT_INSTRUMENT_DIR = APP_DATA_DIR / "instrumented"
    CHECKPOINTS_DIR = APP_DATA_DIR / "checkpoints"

    CPG_ANALYZER_ROOT_DIR = Path(__file__).resolve().parent.parent
    CPG_ANALYZER_JAVA_LIBS_DIR = CPG_ANALYZER_ROOT_DIR / "java_libs"
    ANTLR_PATH = CPG_ANALYZER_JAVA_LIBS_DIR / "antlr-4.13.2-complete.jar"
    CHECKPOINT_SAVER_PATH = CPG_ANALYZER_JAVA_LIBS_DIR / "CheckPointSaver.jar"
