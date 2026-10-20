"""Freeze computations and verify replay without executing archived Python."""
from hashlib import sha256
from pathlib import Path
import platform
import sqlite3

from .calc import evaluate, ALGORITHM_ID
from .core import IntegrityError, digest
from .graph import verify_closure, outdated_sources

COMPUTATION_FILES = ["__init__.py", "core.py", "storage.py", "domain.py", "ingest.py",
                     "graph.py", "calc.py", "datasets.py"]


def source_manifest():
    root = Path(__file__).parent
    return {"algorithm_id": ALGORITHM_ID,
            "files": {name: sha256((root / name).read_bytes()).hexdigest() for name in COMPUTATION_FILES},
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(), "sqlite_version": sqlite3.sqlite_version,
            "decimal_precision": 50, "rounding": "ROUND_HALF_EVEN"}


def validate_dataset(db, payload, artifacts):
    manifest = payload.get("algorithm_manifest")
    if manifest != source_manifest():
        raise IntegrityError("Dataset implementation/environment differs from the running instrument")
    if not set(manifest["files"].values()) <= set(artifacts):
        raise IntegrityError("Dataset computation source files were not retained")
    computed = evaluate(db, payload["cohort_version"], payload["policy_version"])
    if payload.get("result") != computed or payload.get("result_sha256") != digest(computed):
        raise IntegrityError("Dataset output does not match its declared computation")


def freeze(db, entity_id, cohort_version, policy_version, *, expected=None,
           actor="local-operator", reason="frozen descriptive comparison"):
    with db.atomic():
        manifest = source_manifest()
        artifacts = [db.objects.add(Path(__file__).parent / name) for name in COMPUTATION_FILES]
        result = evaluate(db, cohort_version, policy_version)
        return db.capture(entity_id, "dataset", {"cohort_version": cohort_version, "policy_version": policy_version,
                          "algorithm_manifest": manifest, "result": result, "result_sha256": digest(result)},
                          artifacts=artifacts, expected=expected, actor=actor, reason=reason)


def replay(db, dataset_version):
    record = db.get(dataset_version)
    if record["kind"] != "dataset":
        raise IntegrityError("Replay requires a dataset version")
    checked = verify_closure(db, dataset_version)
    p = record["payload"]
    if p["algorithm_manifest"] != source_manifest():
        raise IntegrityError("Replay blocked: restore the recorded source/runtime; archived code is never auto-executed")
    result = evaluate(db, p["cohort_version"], p["policy_version"], historical=True)
    if result != p["result"] or digest(result) != p["result_sha256"]:
        raise IntegrityError("Replay output differs from the frozen dataset")
    return {"ok": True, "dataset_version": dataset_version, "result_sha256": digest(result),
            "stale_inputs": outdated_sources(db, dataset_version), "verified": checked,
            "meaning": "Historical numerical replay succeeded; scientific validity is not established."}
