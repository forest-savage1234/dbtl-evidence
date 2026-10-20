"""Create a source bundle with hashes and optional complete local Git history."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP = {"README.md", "SCOPE.md", "CHANGELOG.md", "pyproject.toml", "CITATION.cff", ".gitignore"}
DIRECTORIES = {"dbtl", "tests", "tools", "docs", "evidence", "examples", ".github"}


def selected_files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not p.is_symlink()
                  and ((len(p.relative_to(ROOT).parts) == 1 and p.name in TOP)
                       or p.relative_to(ROOT).parts[0] in DIRECTORIES)
                  and "__pycache__" not in p.parts and not p.name.endswith((".pyc", "-wal", "-shm")))


def package(destination, *, history=True):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Package destination already exists")
    payloads = {str(p.relative_to(ROOT)): p.read_bytes() for p in selected_files()}
    if history:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "history.bundle"
            subprocess.run(["git", "bundle", "create", str(bundle), "--all"], cwd=ROOT, check=True, capture_output=True)
            payloads["history.bundle"] = bundle.read_bytes()
    payloads["PACKAGE_MANIFEST.json"] = json.dumps({"format": "dbtl-source-bundle:1",
        "sha256": {name: sha256(content).hexdigest() for name, content in sorted(payloads.items())}}, indent=2).encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(payloads.items()):
            info = zipfile.ZipInfo("dbtl-evidence/" + name, date_time=(2026, 10, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return {"package": str(destination), "files": len(payloads), "bytes": destination.stat().st_size,
            "sha256": sha256(destination.read_bytes()).hexdigest(), "history_included": history}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()
    print(json.dumps(package(args.output, history=not args.no_history), indent=2))


if __name__ == "__main__": main()
