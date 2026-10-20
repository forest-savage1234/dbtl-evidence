"""Reproducible synthetic boundary probes for the audited DBTL v1.0 source.

These tests document limits; passing them does not mean the limits are fixed.
Run from the repository root: python3 tools/campaign_probe.py
"""
import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dbtl.core import Instrument, IntegrityError
from dbtl.ingest import FIELDS, ingest_csv
from dbtl.calc import evaluate
from dbtl.datasets import freeze
from dbtl.review import findings

ROOT = Path(__file__).resolve().parents[1]
AUDITED_COMMIT = "b99188386e8b0c60133b09f072b23cd57154b2be"
RESULTS = []


def setup(db, name="A", *, shared=None, extra=None):
    shared = shared or {}
    protocol = shared.get("protocol") or db.capture("protocol:" + name, "protocol", {"name": "SYNTHETIC"})
    extraction = shared.get("extraction") or db.capture("extraction:" + name, "protocol", {"name": "SYNTHETIC"})
    strain = shared.get("strain") or db.capture("strain:" + name, "strain", {"genotype_status": "unverified"})
    calibration = shared.get("calibration") or db.capture("calibration:" + name, "calibration", {
        "analyte_id": "synthetic:product", "response_unit": "area", "concentration_unit": "mg/L",
        "slope": "2", "intercept": "10", "min_response": "10", "max_response": "10000"})
    context = {"medium": "synthetic:medium", "temperature_c": "30", "ph": "7",
               "oxygenation": "aerobic", "vessel": "synthetic:reactor", "batch": "synthetic:batch"}
    culture = db.capture("culture:" + name, "culture", {**context, "strain_version": strain["id"],
        "protocol_version": protocol["id"], **(extra or {})})
    sample = db.capture("sample:" + name, "sample", {"culture_version": culture["id"], "time_h": "24",
        "compartment": "supernatant", "extraction_protocol_version": extraction["id"]})
    return dict(protocol=protocol, extraction=extraction, strain=strain, calibration=calibration,
                culture=culture, sample=sample, context=context)


def measurement(db, root, parts, name="A", response="1010"):
    row = {"measurement_id": "measurement:" + name, "sample_version": parts["sample"]["id"],
        "calibration_version": parts["calibration"]["id"], "analyte_id": "synthetic:product",
        "response": response, "response_unit": "area", "dilution": "1", "qc": "pass",
        "quantification": "quantified", "technical_replicate_id": "tech:1", "run_id": "run:1"}
    path = Path(root) / (name + ".csv")
    with path.open("w", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=FIELDS)
        w.writeheader()
        w.writerow(row)
    return ingest_csv(db, path)["measurement_versions"][0]


def cohort_policy(db, p, measurements, minimum=1, genotype="any"):
    cohort = db.capture("cohort:probe", "cohort", {"measurement_versions": measurements})
    context = {**p["context"], "culture_protocol_version": p["protocol"]["id"], "time_h": "24",
               "compartment": "supernatant", "extraction_protocol_version": p["extraction"]["id"]}
    policy = db.capture("policy:probe", "policy", {"metric": "titer_g_l",
        "analyte_id": "synthetic:product", "context": context,
        "technical_aggregation": "arithmetic_mean", "min_biological_replicates": minimum,
        "genotype_requirement": genotype})
    return cohort, policy


def record(id, reason, observed):
    RESULTS.append({"id": id, "kind": "synthetic scope probe", "reason": reason,
                    "observed": observed, "expectation_met": True})


def main():
    with tempfile.TemporaryDirectory() as tmp, Instrument(Path(tmp) / "state") as db:
        p = setup(db)
        note = Path(tmp) / "assertion.txt"
        note.write_text("SYNTHETIC assertion only: no sequence, reads, or assay.")
        artifact = db.objects.add(note)
        verified = db.capture(p["strain"]["entity_id"], "strain", {"genotype_status": "asserted_verified"},
            expected=p["strain"]["id"], artifacts=[artifact], reason="SYNTHETIC assertion probe")
        # Use an unambiguous current strain dependency in a new culture.
        q = setup(db, "V", shared={**p, "strain": verified})
        m = measurement(db, tmp, q, "V")
        cohort, policy = cohort_policy(db, q, [m], genotype="asserted_verified")
        result = evaluate(db, cohort["id"], policy["id"])
        assert len(result["included"]) == 1
        record("DE-01", "Any retained artifact satisfies asserted_verified; artifact content is not genotype verification.",
               {"asserted_verified_accepted": True, "included_measurements": 1})

    with tempfile.TemporaryDirectory() as tmp, Instrument(Path(tmp) / "state") as db:
        p = setup(db, extra={"extensions": {"lab:oxygen_trajectory": "constant"}})
        q = setup(db, "B", shared=p, extra={"extensions": {"lab:oxygen_trajectory": "oscillating"}})
        cohort, policy = cohort_policy(db, p, [measurement(db,tmp,p), measurement(db,tmp,q,"B")], minimum=2)
        r = evaluate(db, cohort["id"], policy["id"])
        assert len(r["included"]) == 2 and r["summaries"][0]["biological_n"] == 2
        record("DE-02", "Distinct trajectory extensions are retained but ignored by the ten-field comparison policy.",
               {"included_measurements": 2, "biological_n": 2, "different_trajectory_extensions_pooled": True})

    with tempfile.TemporaryDirectory() as tmp, Instrument(Path(tmp) / "state") as db:
        p = setup(db)
        cohort, policy = cohort_policy(db, p, [measurement(db,tmp,p)])
        dataset = freeze(db,"dataset:probe",cohort["id"],policy["id"])
        db.capture("decision:probe","decision",{"dataset_version":dataset["id"],
            "selected_strain_versions":[p["strain"]["id"]],"rationale":"SYNTHETIC fixed evidence set."})
        before = len(findings(db))
        q = setup(db,"NEW",shared={"protocol":p["protocol"],"extraction":p["extraction"],"calibration":p["calibration"]})
        new = measurement(db,tmp,q,"NEW",response="9010")
        after = len(findings(db))
        assert before == after == 0 and new not in cohort["payload"]["measurement_versions"]
        record("DE-03", "New independent eligible evidence outside the frozen cohort does not trigger reassessment.",
               {"pending_before":before,"pending_after_new_evidence":after,"new_evidence_in_frozen_cohort":False})

    with tempfile.TemporaryDirectory() as tmp, Instrument(Path(tmp) / "state") as db:
        p = setup(db, extra={"extensions":{"lab:physical_origin":"same-physical-culture"}})
        q = setup(db,"ALIAS",shared=p,extra={"extensions":{"lab:physical_origin":"same-physical-culture"}})
        cohort, policy = cohort_policy(db,p,[measurement(db,tmp,p),measurement(db,tmp,q,"ALIAS")],minimum=2)
        r = evaluate(db,cohort["id"],policy["id"])
        assert r["summaries"][0]["biological_n"] == 2
        record("DE-04", "Distinct culture entity labels are counted separately even when an extension declares a shared physical origin.",
               {"declared_shared_physical_origin":True,"reported_biological_n":2,"rank":r["summaries"][0]["rank"]})

    with tempfile.TemporaryDirectory() as tmp, Instrument(Path(tmp) / "state") as db:
        p = setup(db)
        q = setup(db,"B",shared=p,extra={"batch":"synthetic:other-batch"})
        cohort, policy = cohort_policy(db,p,[measurement(db,tmp,p),measurement(db,tmp,q,"B")])
        r = evaluate(db,cohort["id"],policy["id"])
        assert len(r["included"])==1 and "context_mismatch:batch" in r["excluded"][0]["reasons"]
        record("DE-05", "Positive control: a supported context mismatch is explicitly excluded.",
               {"included":1,"excluded":1,"reasons":r["excluded"][0]["reasons"]})
        cal = p["calibration"]
        db.capture(cal["entity_id"],"calibration",{**cal["payload"],"slope":"4"},expected=cal["id"],reason="SYNTHETIC correction")
        blocked = False
        try:
            evaluate(db,cohort["id"],policy["id"])
        except IntegrityError:
            blocked = True
        assert blocked
        record("DE-06", "Positive control: a changed dependency blocks a new current comparison.",
               {"current_comparison_blocked":blocked})
    print(json.dumps({"audited_baseline_commit":AUDITED_COMMIT,
        "production_source_sha256":{str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/"dbtl").glob("*.py"))},
        "python":platform.python_version(),"results":RESULTS},indent=2))


if __name__ == "__main__":
    main()
