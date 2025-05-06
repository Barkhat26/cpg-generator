from shutil import rmtree
from pathlib import Path

from config import Config
from dynamic.checkpoint_manager import CheckpointManager
from utils.other import escape_fp


IMPORT_LINE = "import cpganalyzer.CheckPointSaver;\n"


class InstrumentModification:
    def __init__(self, line: int, content: str):
        self.line = line
        self.content = content


class FileModification:
    def __init__(self, out_file: Path, modifications: list[InstrumentModification]):
        self.out_file = out_file
        self.modifications = modifications

class InstrumentTool:
    def __init__(self, project_name: str, checkpoint_manager: CheckpointManager = None):
        self.project_name = project_name
        self.checkpointManager = checkpoint_manager

    def instrument(self) -> list[FileModification]:
        if not self.checkpointManager or not self.checkpointManager.taint_flows:
            return []

        sinks = [tf.sink for tf in self.checkpointManager.taint_flows]
        unique_sinks = []
        for sink in sinks:
            if sink not in unique_sinks:
                unique_sinks.append(sink)

        infos = []
        for sink in unique_sinks:
            info = {
                "id": self.checkpointManager.sink_to_checkpoint_id[sink.shared_id],
                "line": sink.line,
                "file": sink.file,
                "argument": sink.optional_properties["checkpoint"]
            }
            infos.append(info)

        groups = dict()
        for info in infos:
            if info["file"] in groups:
                groups[info["file"]].append(info)
            else:
                groups[info["file"]] = [info]

        return [self.modify_file(file, info_group) for file, info_group in groups.items()]

    def modify_file(self, file: Path | str, info_group: list[dict]) -> FileModification:
        _file = Path(file)
        instrument_modifications: list[InstrumentModification] = []

        with open(_file) as f:
            content = f.readlines()

        line_with_package = -1
        for idx, line in enumerate(content):
            if line.startswith("package"):
                line_with_package = idx

        content.insert(line_with_package + 1, IMPORT_LINE)
        instrument_modifications.append(InstrumentModification(line_with_package + 1, IMPORT_LINE))
        info_group = sorted(info_group, key=lambda x: x["line"])
        checkpoint_line_offset = 0  # 1 потому что уже была вставка import

        for info in info_group:
            id_ = info["id"]
            argument = info["argument"]
            checkpoint = f'new CheckPointSaver("{escape_fp(Config.CHECKPOINTS_DIR / self.project_name)}").saveToFile("ch_{id_}", {argument});\n'
            content.insert(info["line"] + checkpoint_line_offset, checkpoint)
            instrument_modifications.append(InstrumentModification(info["line"] + checkpoint_line_offset, checkpoint))
            checkpoint_line_offset += 1

        out_dir = Config.DEFAULT_INSTRUMENT_DIR / self.project_name

        if not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / _file.name

        with open(out_file, "w") as f:
            f.write("".join(content))

        return FileModification(out_file, instrument_modifications)

    def clean(self):
        out_dir = Config.DEFAULT_INSTRUMENT_DIR / self.project_name

        if out_dir.exists():
            rmtree(out_dir)
