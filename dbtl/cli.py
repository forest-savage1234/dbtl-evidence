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
    p = argparse.ArgumentParser(description="DBTL evidence: scoped decision packets, retained evidence and reassessment")
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
    q = commands.add_parser("demo2"); q.add_argument("--output", default="scoped-demo-output")
    q = commands.add_parser("assessment-summary"); q.add_argument("subject_version")
    q = commands.add_parser("pool-snapshot"); q.add_argument("entity_id"); q.add_argument("pool_version"); q.add_argument("--expected"); q.add_argument("--reason", required=True)
    q = commands.add_parser("pool-replay"); q.add_argument("snapshot_version")
    q = commands.add_parser("watch-add"); q.add_argument("entity_id"); q.add_argument("target_version"); q.add_argument("snapshot_version"); q.add_argument("--basis", required=True)
    q = commands.add_parser("watch-check"); q.add_argument("watch_version")
    q = commands.add_parser("watch-list"); q.add_argument("--all", action="store_true")
    q = commands.add_parser("watch-review"); q.add_argument("watch_version"); q.add_argument("fingerprint"); q.add_argument("--disposition", choices=["retain_historical","retire"], required=True); q.add_argument("--basis", required=True)
    q = commands.add_parser("quantity-capture"); q.add_argument("entity_id"); q.add_argument("source"); q.add_argument("subject_version"); q.add_argument("--row",type=int,required=True); q.add_argument("--value-column",required=True); q.add_argument("--unit-column",required=True); q.add_argument("--pair-column",required=True); q.add_argument("--basis",required=True); q.add_argument("--measurand",required=True); q.add_argument("--origin",choices=["local","literature","simulation","synthetic"],default="local")
    q = commands.add_parser("derive"); q.add_argument("entity_id"); q.add_argument("--numerator",action="append",required=True); q.add_argument("--denominator",action="append",required=True); q.add_argument("--metric",required=True); q.add_argument("--estimator",choices=["ratio_of_means","mean_of_paired_ratios"],required=True)
    q = commands.add_parser("quantity-replay"); q.add_argument("version")
    q = commands.add_parser("unit-assign"); q.add_argument("subject_version"); q.add_argument("unit_version"); q.add_argument("--basis",required=True); q.add_argument("--expected")
    q = commands.add_parser("uncertainty-freeze"); q.add_argument("entity_id"); q.add_argument("measurement_version"); q.add_argument("assay_profile_version"); q.add_argument("source")
    q = commands.add_parser("claim-import"); q.add_argument("entity_id"); q.add_argument("report"); q.add_argument("source"); q.add_argument("--origin",choices=["literature","synthetic_fixture"],required=True); q.add_argument("--intended-use",required=True); q.add_argument("--target-domain",required=True); q.add_argument("--expected"); q.add_argument("--reason",required=True)
    q = commands.add_parser("packet"); q.add_argument("entity_id"); q.add_argument("cohort_version"); q.add_argument("policy_version"); q.add_argument("snapshot_version"); q.add_argument("--reference",action="append",default=[]); q.add_argument("--expected"); q.add_argument("--reason",required=True)
    for command in ("packet-replay","packet-status"):
        q=commands.add_parser(command);q.add_argument("packet_version")
    q=commands.add_parser("packet-report");q.add_argument("packet_version");q.add_argument("--output",required=True)
    q=commands.add_parser("advance");q.add_argument("entity_id");q.add_argument("packet_version");q.add_argument("selected_strains",nargs="+");q.add_argument("--rationale",required=True);q.add_argument("--expected")
    q = commands.add_parser("backup"); q.add_argument("--output", required=True)
    q = commands.add_parser("restore"); q.add_argument("archive"); q.add_argument("destination")
    return p


def dispatch(db, a):
    if a.command == "init": return {"root": str(db.root), "schema": 1}
    if a.command == "capture":
        from .contracts import unique_object
        path=Path(a.json_file)
        if path.stat().st_size>4*1024*1024: raise IntegrityError("Capture JSON exceeds 4 MiB")
        payload = json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=unique_object)
        if not isinstance(payload, dict): raise IntegrityError("Capture payload must be a JSON object")
        extra = []
        for pair in a.dependency:
            if "=" not in pair: raise IntegrityError("Additional dependencies use role=version")
            role, version = pair.split("=", 1); extra.append({"role": role, "version_id": version})
        try: refs=dependencies(a.kind,payload)
        except IntegrityError: raise
        except (KeyError,TypeError,AttributeError,ValueError,RecursionError) as exc: raise IntegrityError("Malformed capture dependencies") from exc
        return db.put(a.entity_id, a.kind, payload, dependencies=refs+extra,
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
    if a.command == "assessment-summary":
        from .assessments import summary
        return summary(db,a.subject_version)
    if a.command in {"pool-snapshot","pool-replay"}:
        from .pools import snapshot,replay_snapshot
        return snapshot(db,a.entity_id,a.pool_version,expected=a.expected,reason=a.reason,actor=a.actor) if a.command=="pool-snapshot" else replay_snapshot(db,a.snapshot_version)
    if a.command.startswith("watch-"):
        from .watches import watch,status,pending,acknowledge as watch_ack
        if a.command=="watch-add":return watch(db,a.entity_id,a.target_version,a.snapshot_version,basis=a.basis,actor=a.actor)
        if a.command=="watch-check":return status(db,a.watch_version)
        if a.command=="watch-list":return pending(db,include_acknowledged=a.all)
        return watch_ack(db,a.watch_version,a.fingerprint,disposition=a.disposition,basis=a.basis,actor=a.actor)
    if a.command in {"quantity-capture","derive","quantity-replay"}:
        from .quantities import capture_quantity,derive,replay_result
        if a.command=="quantity-replay":return replay_result(db,a.version)
        if a.command=="derive":return derive(db,a.entity_id,a.numerator,a.denominator,metric=a.metric,estimator=a.estimator,actor=a.actor)
        return capture_quantity(db,a.entity_id,a.source,row=a.row,value_column=a.value_column,unit_column=a.unit_column,pair_column=a.pair_column,subject_version=a.subject_version,basis=a.basis,measurand_id=a.measurand,origin=a.origin,actor=a.actor)
    if a.command=="unit-assign":
        from .units import assign
        return assign(db,a.subject_version,a.unit_version,basis=a.basis,expected=a.expected,actor=a.actor)
    if a.command=="uncertainty-freeze":
        from .uncertainty import freeze_uncertainty
        return freeze_uncertainty(db,a.entity_id,a.measurement_version,a.assay_profile_version,a.source,actor=a.actor)
    if a.command=="claim-import":
        from .handoff import receive
        return receive(db,a.entity_id,a.report,a.source,origin=a.origin,intended_use=a.intended_use,target_domain=a.target_domain,expected=a.expected,reason=a.reason,actor=a.actor)
    if a.command in {"packet","packet-replay","packet-status","packet-report","advance"}:
        from .packets import freeze as packet_freeze,replay as packet_replay,status as packet_status,render
        if a.command=="packet":return packet_freeze(db,a.entity_id,a.cohort_version,a.policy_version,a.snapshot_version,reference_versions=a.reference,expected=a.expected,reason=a.reason,actor=a.actor)
        if a.command=="packet-replay":return packet_replay(db,a.packet_version)
        if a.command=="packet-status":return packet_status(db,a.packet_version)
        if a.command=="packet-report":
            path=Path(a.output);path.write_text(render(db,a.packet_version),encoding="utf-8");return {"report":str(path.resolve())}
        return db.capture(a.entity_id,"advance",{"packet_version":a.packet_version,"selected_strain_versions":a.selected_strains,"rationale":a.rationale},expected=a.expected,actor=a.actor)
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
        if a.command == "demo2":
            from .demo2 import run_demo2
            result=run_demo2(a.output)
            print(json.dumps({"output":str(Path(a.output).resolve()),"audit":result["audit"],"initial_top":result["initial_top"],"reassessed_top":result["reassessed_top"],"pool_growth_alert":result["pool_growth_alert"],"historical_replay_ok":result["historical_replay"]["ok"]},indent=2))
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
