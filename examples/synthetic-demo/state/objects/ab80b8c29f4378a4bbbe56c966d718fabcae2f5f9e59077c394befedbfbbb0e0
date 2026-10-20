"""Local CLI. No network listener, credentials, or external application writes."""
import argparse
import json
import sqlite3
from pathlib import Path
import sys

from . import __version__
from .core import Instrument, IntegrityError, KINDS
from .domain import dependencies
from .ingest import ingest_csv
from .datasets import freeze, replay
from .graph import impact
from .review import findings, acknowledge, recalibrate, refresh_cohort
from .report import render_report


def parser():
    p = argparse.ArgumentParser(description="DBTL evidence: local titer comparison and correction review")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--root", default="dbtl-state", help="Local instrument state directory")
    p.add_argument("--actor", default="local-operator", help="Operator assertion, not authenticated identity")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    q = commands.add_parser("capture"); q.add_argument("entity_id"); q.add_argument("kind", choices=sorted(KINDS)); q.add_argument("json_file"); q.add_argument("--expected"); q.add_argument("--reason", required=True); q.add_argument("--evidence", action="append", default=[]); q.add_argument("--dependency", action="append", default=[], help="Additional role=version input")
    q = commands.add_parser("list"); q.add_argument("--kind", choices=sorted(KINDS)); q.add_argument("--all", action="store_true")
    q = commands.add_parser("show"); q.add_argument("version_id")
    q = commands.add_parser("ingest"); q.add_argument("csv_file")
    q = commands.add_parser("cohort"); q.add_argument("entity_id"); q.add_argument("measurements", nargs="+"); q.add_argument("--expected"); q.add_argument("--reason", required=True)
    q = commands.add_parser("freeze"); q.add_argument("entity_id"); q.add_argument("cohort_version"); q.add_argument("policy_version"); q.add_argument("--expected"); q.add_argument("--reason", required=True)
    q = commands.add_parser("replay"); q.add_argument("dataset_version")
    q = commands.add_parser("impact"); q.add_argument("version_id"); q.add_argument("--path-limit", type=int, default=256)
    q = commands.add_parser("reviews"); q.add_argument("--all", action="store_true")
    q = commands.add_parser("review"); q.add_argument("finding_id"); q.add_argument("--disposition", choices=["retain_historical", "retire"], required=True); q.add_argument("--note", required=True); q.add_argument("--reviewer", required=True)
    q = commands.add_parser("recalibrate"); q.add_argument("measurement_version"); q.add_argument("calibration_version"); q.add_argument("--reason", required=True)
    q = commands.add_parser("refresh-cohort"); q.add_argument("cohort_version"); q.add_argument("--reason", required=True)
    q = commands.add_parser("decide"); q.add_argument("entity_id"); q.add_argument("dataset_version"); q.add_argument("selected_strains", nargs="+"); q.add_argument("--rationale", required=True); q.add_argument("--expected")
    commands.add_parser("audit")
    q = commands.add_parser("report"); q.add_argument("--output", required=True)
    q = commands.add_parser("demo"); q.add_argument("--output", default="demo-output")
    q = commands.add_parser("backup"); q.add_argument("--output", required=True)
    q = commands.add_parser("restore"); q.add_argument("archive"); q.add_argument("destination")
    return p


def dispatch(db, a):
    if a.command == "init": return {"root": str(db.root), "schema": 1}
    if a.command == "capture":
        payload = json.loads(Path(a.json_file).read_text(encoding="utf-8"))
        if not isinstance(payload, dict): raise IntegrityError("Capture payload must be a JSON object")
        extra = []
        for pair in a.dependency:
            if "=" not in pair: raise IntegrityError("Additional dependencies use role=version")
            role, version = pair.split("=", 1); extra.append({"role": role, "version_id": version})
        return db.put(a.entity_id, a.kind, payload, dependencies=dependencies(a.kind, payload)+extra,
                      artifacts=[db.objects.add(p) for p in a.evidence], expected=a.expected, actor=a.actor, reason=a.reason)
    if a.command == "list": return db.versions(a.kind, heads_only=not a.all)
    if a.command == "show": return db.get(a.version_id)
    if a.command == "ingest": return ingest_csv(db, a.csv_file, actor=a.actor)
    if a.command == "cohort": return db.capture(a.entity_id, "cohort", {"measurement_versions": a.measurements}, expected=a.expected, actor=a.actor, reason=a.reason)
    if a.command == "freeze": return freeze(db, a.entity_id, a.cohort_version, a.policy_version, expected=a.expected, actor=a.actor, reason=a.reason)
    if a.command == "replay": return replay(db, a.dataset_version)
    if a.command == "impact": return impact(db, a.version_id, max_path_steps=a.path_limit)
    if a.command == "reviews": return findings(db, include_acknowledged=a.all)
    if a.command == "review": return acknowledge(db, a.finding_id, disposition=a.disposition, note=a.note, actor=a.reviewer)
    if a.command == "recalibrate": return recalibrate(db, a.measurement_version, a.calibration_version, actor=a.actor, reason=a.reason)
    if a.command == "refresh-cohort": return refresh_cohort(db, a.cohort_version, actor=a.actor, reason=a.reason)
    if a.command == "decide": return db.capture(a.entity_id, "decision", {"dataset_version": a.dataset_version, "selected_strain_versions": a.selected_strains, "rationale": a.rationale}, expected=a.expected, actor=a.actor, reason="explicit experimental selection")
    if a.command == "audit": return db.verify()
    if a.command == "backup":
        from .backup import backup
        return backup(db, a.output)
    if a.command == "report":
        path = Path(a.output); path.write_text(render_report(db), encoding="utf-8")
        return {"report": str(path.resolve()), "audit_ok": db.verify()["ok"]}
    raise IntegrityError("Unknown operation")


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        if a.command == "restore":
            from .backup import restore
            print(json.dumps(restore(a.archive, a.destination), indent=2))
            return 0
        if a.command == "demo":
            from .demo import run_demo
            result = run_demo(a.output)
            print(json.dumps({"output": str(Path(a.output).resolve()), "audit": result["audit"],
                              "original_winner": result["original"][0]["strain_id"], "corrected_winner": result["corrected"][0]["strain_id"]}, indent=2))
            return 0
        if a.command != "init" and not (Path(a.root) / "registry.sqlite").is_file():
            raise IntegrityError("No registry at this path; run init first")
        with Instrument(a.root) as db:
            result = dispatch(db, a)
            print(json.dumps(result, indent=2))
            return 1 if isinstance(result, dict) and result.get("ok") is False else 0
    except (IntegrityError, OSError, json.JSONDecodeError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
