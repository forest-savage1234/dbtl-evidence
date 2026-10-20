"""Run a real gate, record its evidence, then commit and tag a scoped release."""
import hashlib
import json
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys
import time
import unittest
import importlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.successes = []

    def addSuccess(self, test):
        self.successes.append(test.id())
        super().addSuccess(test)


def main():
    version = sys.argv[1]
    if not re.fullmatch(r"(?:0\.[1-9]|1\.0)", version):
        raise SystemExit("Use 0.1 through 1.0")
    (ROOT / "dbtl/__init__.py").write_text(
        '"""Local DBTL evidence instrument; see SCOPE.md."""\n__version__ = "' + version + '.0"\n')
    config = ROOT / "pyproject.toml"
    config.write_text(re.sub(r'version = "[^"]+"', 'version = "' + version + '.0"', config.read_text()))
    for cached in (ROOT / "dbtl/__pycache__").glob("__init__*.pyc"):
        cached.unlink()
    importlib.invalidate_caches()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
    demonstration = None
    if version == "1.0" and result.wasSuccessful():
        from dbtl.demo import run_demo
        demo = run_demo(ROOT / "examples/synthetic-demo")
        demonstration = {"data": demo["data"], "original_winner": demo["original"][0]["strain_id"],
                         "corrected_winner": demo["corrected"][0]["strain_id"],
                         "historical_replay_ok": demo["historical_replay"]["ok"],
                         "current_replay_ok": demo["current_replay"]["ok"], "audit_ok": demo["audit"]["ok"]}
        if not all(demonstration[k] for k in ["historical_replay_ok", "current_replay_ok", "audit_ok"]):
            raise SystemExit("Packaged demonstration failed")
    files = sorted([*ROOT.glob("dbtl/*.py"), *ROOT.glob("tests/*.py"), *ROOT.glob("tools/*.py")])
    evidence = {"release": version, "status": "passed" if result.wasSuccessful() else "failed",
                "tests_run": result.testsRun, "passed_tests": result.successes,
                "failures": [(t.id(), err) for t, err in result.failures + result.errors],
                "skipped": [(t.id(), why) for t, why in result.skipped],
                "elapsed_seconds": time.perf_counter() - start,
                "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                "platform": platform.platform(),
                "demonstration": demonstration,
                "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (ROOT / "evidence" / ("v" + version + ".json")).write_text(json.dumps(evidence, indent=2) + "\n")
    if not result.wasSuccessful() or result.skipped:
        raise SystemExit(1)
    for args in [["add", "."], ["-c", "user.name=Codex", "-c", "user.email=codex@local.invalid", "commit", "-m", "v"+version+": scoped evidence gate passed"], ["tag", "v"+version]]:
        subprocess.run(["git", *args], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
