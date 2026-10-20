"""Synthetic end-to-end counterfactual, including a deliberately reversed ranking."""
import csv
import json
from pathlib import Path

from .core import Instrument, IntegrityError
from .ingest import FIELDS, ingest_csv
from .datasets import freeze, replay
from .review import findings, acknowledge, recalibrate, refresh_cohort
from .report import render_report


def run_demo(destination):
    out = Path(destination).resolve()
    if out.exists() and any(out.iterdir()):
        raise IntegrityError("Demo destination must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    with Instrument(out / "state") as db:
        protocol = db.capture("demo:culture-protocol", "protocol", {"name": "SYNTHETIC culture protocol"})
        extraction = db.capture("demo:extraction-protocol", "protocol", {"name": "SYNTHETIC extraction protocol"})
        recipient = db.capture("demo:strain-B", "strain", {"name": "synthetic reference", "genotype_status": "unverified"})
        donor = db.capture("demo:donor-design", "design", {"name": "synthetic intended construct"})
        activity = db.put("demo:construction", "activity", {"operation": "SYNTHETIC edit event"}, dependencies=[
            {"role": "recipient", "version_id": recipient["id"]}, {"role": "donor", "version_id": donor["id"]},
            {"role": "protocol", "version_id": protocol["id"]}])
        engineered = db.put("demo:strain-A", "strain", {"name": "synthetic engineered strain", "genotype_status": "unverified"}, dependencies=[{"role": "built_by", "version_id": activity["id"]}])
        calibrations = {name: db.capture("demo:calibration-" + name, "calibration", {
            "analyte_id": "demo:product", "response_unit": "area", "concentration_unit": "mg/L",
            "slope": "2", "intercept": "10", "min_response": "10", "max_response": "10000"}) for name in ["A", "B"]}
        context = {"medium": "demo:defined-medium", "temperature_c": "30", "ph": "7", "oxygenation": "shaken-aerobic",
                   "vessel": "demo:flask", "batch": "demo:batch-1"}
        rows = []
        for name, strain, responses in [("A1", engineered, ["1110", "1310", "9"]), ("A2", engineered, ["1210"]),
                                         ("B1", recipient, ["1010"]), ("B2", recipient, ["1050"]), ("C1", engineered, ["2010"])]:
            culture = db.capture("demo:culture-" + name, "culture", {**context, "strain_version": strain["id"],
                "protocol_version": protocol["id"], "batch": "demo:other-batch" if name == "C1" else context["batch"]})
            sample = db.capture("demo:sample-" + name, "sample", {"culture_version": culture["id"], "time_h": "24",
                "compartment": "supernatant", "extraction_protocol_version": extraction["id"]})
            cal = calibrations["B" if name.startswith("B") else "A"]
            for index, response in enumerate(responses, 1):
                rows.append({"measurement_id": f"demo:measurement-{name}-{index}", "sample_version": sample["id"],
                             "calibration_version": cal["id"], "analyte_id": "demo:product", "response": response,
                             "response_unit": "area", "dilution": "1", "qc": "pass",
                             "quantification": "below_loq" if response == "9" else "quantified",
                             "technical_replicate_id": f"tech:{index}", "run_id": "demo:run-1"})
        raw = out / "synthetic_peak_areas.csv"
        with raw.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        imported = ingest_csv(db, raw, actor="synthetic-demo")
        cohort = db.capture("demo:cohort", "cohort", {"measurement_versions": imported["measurement_versions"]})
        policy = db.capture("demo:policy", "policy", {"metric": "titer_g_l", "analyte_id": "demo:product",
            "context": {**context, "culture_protocol_version": protocol["id"], "time_h": "24", "compartment": "supernatant", "extraction_protocol_version": extraction["id"]},
            "technical_aggregation": "arithmetic_mean", "min_biological_replicates": 2, "genotype_requirement": "any"})
        before = freeze(db, "demo:dataset", cohort["id"], policy["id"], actor="synthetic-demo")
        decision = db.capture("demo:decision", "decision", {"dataset_version": before["id"], "selected_strain_versions": [engineered["id"]],
            "rationale": "SYNTHETIC: A has the larger eligible descriptive mean; this is not significance evidence."}, actor="synthetic-demo")
        (out / "original.html").write_text(render_report(db, title="Synthetic comparison · original evidence"), encoding="utf-8")
        old_cal = calibrations["A"]
        corrected = db.capture(old_cal["entity_id"], "calibration", {**old_cal["payload"], "slope": "4"}, expected=old_cal["id"],
                               actor="synthetic-demo", reason="SYNTHETIC deliberate correction: calibration slope doubled")
        queue = findings(db)
        (out / "correction-review.html").write_text(render_report(db, title="Synthetic correction · decisions need review"), encoding="utf-8")
        for finding in queue:
            acknowledge(db, finding["finding_id"], disposition="retire" if finding["target_kind"] == "decision" else "retain_historical",
                        note="SYNTHETIC reviewed correction; preserve old record and explicitly recompute.", actor="synthetic-reviewer")
        for version in imported["measurement_versions"]:
            if db.get(version)["payload"]["calibration_version"] == old_cal["id"]:
                recalibrate(db, version, corrected["id"], actor="synthetic-reviewer", reason="SYNTHETIC apply corrected calibration")
        revised_cohort = refresh_cohort(db, cohort["id"], actor="synthetic-reviewer", reason="SYNTHETIC include explicit revised members")
        after = freeze(db, before["entity_id"], revised_cohort["id"], policy["id"], expected=before["id"], actor="synthetic-reviewer", reason="SYNTHETIC recomputation")
        new_decision = db.capture(decision["entity_id"], "decision", {"dataset_version": after["id"], "selected_strain_versions": [recipient["id"]],
            "rationale": "SYNTHETIC: corrected calibration reverses the descriptive ranking; B now has the larger mean."},
            expected=decision["id"], actor="synthetic-reviewer", reason="SYNTHETIC explicit decision reassessment")
        results = {"data": "SYNTHETIC ONLY", "original": before["payload"]["result"]["summaries"], "corrected": after["payload"]["result"]["summaries"],
                   "initial_review_findings": queue, "remaining_pending_findings": findings(db),
                   "historical_replay": replay(db, before["id"]), "current_replay": replay(db, after["id"]), "audit": db.verify(),
                   "original_dataset_version": before["id"], "current_dataset_version": after["id"], "current_decision_version": new_decision["id"]}
        (out / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        (out / "report.html").write_text(render_report(db, title="Synthetic demonstration · reconstructed and reassessed"), encoding="utf-8")
        return results
