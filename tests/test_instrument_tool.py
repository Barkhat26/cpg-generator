from pathlib import Path

from dynamic.instrument_tool import InstrumentTool


def test_command_executor():
    tool = InstrumentTool("command_executor")
    file = Path(__file__).resolve().parent / "assets" / "original_command_executor" / "CommandExecutor.java"
    info_group = [{
        "id": 1,
        "line": 11,
        "file": file,
        "argument": "command",
    }]
    file_modification = tool.modify_file(file, info_group)

    with open(file_modification.out_file) as f:
        content = f.readlines()

    modifications = file_modification.modifications
    assert content[0] == modifications[0].content
    assert content[11] == modifications[1].content

    tool.clean()