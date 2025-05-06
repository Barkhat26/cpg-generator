import os
import difflib
from pathlib import Path

SNAPSHOT_DIR = Path("snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)

def list_files(directory):
    return [f for f in Path(directory).rglob("*") if f.is_file()]

def rel_path(file, base):
    return os.path.relpath(file, base)

def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readlines()
    except Exception:
        return []

def write_patch(patch_lines, snapshot_name):
    snapshot_path = SNAPSHOT_DIR / f"{snapshot_name}.diff"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.writelines(patch_lines)

def create_snapshot(code_dir, snapshot_name):
    code_dir = Path(code_dir)
    patch_lines = []

    for file in list_files(code_dir):
        rel = rel_path(file, code_dir)
        original = read_file(file)
        backup_path = file  # патч будет сравниваться с тем же путём позже

        # для первой версии просто сохраним как diff "от пустого к текущему"
        empty = []
        diff = difflib.unified_diff(
            empty, original,
            fromfile=f"/dev/null",
            tofile=str(rel),
            lineterm=""
        )
        patch_lines.extend(line + "\n" for line in diff)

    write_patch(patch_lines, snapshot_name)
    print(f"[+] Snapshot '{snapshot_name}' created.")

def restore_snapshot(code_dir, snapshot_name):
    import subprocess

    code_dir = Path(code_dir)
    snapshot_path = SNAPSHOT_DIR / f"{snapshot_name}.diff"
    if not snapshot_path.exists():
        print(f"[!] Snapshot '{snapshot_name}' not found.")
        return

    # сохраняем патч-файл
    patch_cmd = ["patch", "-p0", "-d", str(code_dir), "-R"]
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            subprocess.run(patch_cmd, input=f.read(), text=True, check=True)
            print(f"[+] Snapshot '{snapshot_name}' restored (reversed patch).")
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to apply patch: {e}")

def list_snapshots():
    snaps = sorted(SNAPSHOT_DIR.glob("*.diff"))
    return [snap.stem for snap in snaps]
