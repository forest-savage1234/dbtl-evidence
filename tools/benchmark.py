"""Reproducible local measurements, not an enterprise-scale performance claim."""
import argparse
import csv
import json
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dbtl.core import Instrument
from dbtl.graph import closure, impact
from dbtl.ingest import ingest_csv, FIELDS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes", type=int, default=2000)
    parser.add_argument("--measurements", type=int, default=1000)
    parser.add_argument("--output", default="evidence/benchmark.json")
    args = parser.parse_args()
    result = {"scope": "Synthetic local single-process benchmark; no relative vendor or multiomics-scale claim",
              "python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "platform": platform.platform()}
    with tempfile.TemporaryDirectory() as root, Instrument(Path(root) / "state") as db:
        start = time.perf_counter()
        with db.atomic():
            first = previous = db.put("node:0", "design", {})
            for i in range(1, args.nodes):
                previous = db.put(f"node:{i}", "design", {}, dependencies=[{"role": "input", "version_id": previous["id"]}])
        result["graph_nodes"] = args.nodes
        result["graph_insert_seconds"] = time.perf_counter() - start
        start = time.perf_counter(); reached = closure(db, first["id"], downstream=True)
        result["graph_reachability_seconds"] = time.perf_counter() - start
        result["reached_nodes"] = len(reached)
        start = time.perf_counter(); explained = impact(db, first["id"], max_path_steps=32)
        result["bounded_explanation_seconds"] = time.perf_counter() - start
        result["explained_nodes"] = len(explained)
        from tests.support import setup_assay
        parts = setup_assay(db)
        raw = Path(root) / "large.csv"
        with raw.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader()
            for i in range(args.measurements):
                writer.writerow({"measurement_id": f"m:{i}", "sample_version": parts["sample"]["id"], "calibration_version": parts["calibration"]["id"],
                    "analyte_id": "CHEBI:synthetic-product", "response": "1010", "response_unit": "area", "dilution": "1", "qc": "pass",
                    "quantification": "quantified", "technical_replicate_id": f"tech:{i}", "run_id": "run:benchmark"})
        start = time.perf_counter(); imported = ingest_csv(db, raw)
        result["csv_measurements"] = imported["rows"]
        result["csv_bytes"] = raw.stat().st_size
        result["csv_ingestion_seconds"] = time.perf_counter() - start
        start = time.perf_counter(); audit = db.verify()
        result["audit_seconds"] = time.perf_counter() - start
        result["audit_ok"] = audit["ok"]
        if len(reached) != args.nodes - 1 or imported["rows"] != args.measurements or not audit["ok"]:
            raise SystemExit("Benchmark correctness check failed")
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
