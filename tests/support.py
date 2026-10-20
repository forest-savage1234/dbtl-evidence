import csv
from pathlib import Path

from dbtl.ingest import FIELDS


def setup_assay(db, prefix="A", strain=None, culture=None, calibration=None, protocol=None, extraction=None, **context):
    protocol = protocol or db.put("protocol:" + prefix, "protocol", {"name": "synthetic culture protocol"})
    extraction = extraction or db.put("extraction:" + prefix, "protocol", {"name": "synthetic extraction"})
    strain = strain or db.put("strain:" + prefix, "strain", {"genotype_status": "unverified"})
    culture_payload = {"strain_version": strain["id"], "protocol_version": protocol["id"],
                       "medium": "defined-medium:1", "temperature_c": "30", "ph": "7",
                       "oxygenation": "shaken-aerobic", "vessel": "flask:250mL", "batch": "batch:1"}
    culture_payload.update(context)
    culture = culture or db.capture("culture:" + prefix, "culture", culture_payload)
    sample = db.capture("sample:" + prefix, "sample", {"culture_version": culture["id"], "time_h": "24",
                        "compartment": "supernatant", "extraction_protocol_version": extraction["id"]})
    calibration = calibration or db.capture("calibration:" + prefix, "calibration", {
        "analyte_id": "demo:product", "response_unit": "area", "concentration_unit": "mg/L",
        "slope": "2", "intercept": "10", "min_response": "10", "max_response": "10000"})
    return {"protocol": protocol, "extraction": extraction, "strain": strain,
            "culture": culture, "sample": sample, "calibration": calibration}


def write_csv(path, parts, *, response="1010", rows=None, run="run:1"):
    base = {"measurement_id": "measurement:" + parts["sample"]["entity_id"].split(":")[-1],
            "sample_version": parts["sample"]["id"], "calibration_version": parts["calibration"]["id"],
            "analyte_id": "demo:product", "response": response, "response_unit": "area",
            "dilution": "1", "qc": "pass", "quantification": "quantified", "technical_replicate_id": "tech:1", "run_id": run}
    rows = rows if rows is not None else [base]
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return base


def policy_payload(parts, **changes):
    c, s = parts["culture"]["payload"], parts["sample"]["payload"]
    payload = {"metric": "titer_g_l", "analyte_id": "demo:product",
               "context": {k: c[k] for k in ("medium", "temperature_c", "ph", "oxygenation", "vessel", "batch")},
               "technical_aggregation": "arithmetic_mean", "min_biological_replicates": 2,
               "genotype_requirement": "any"}
    payload["context"].update({"culture_protocol_version": c["protocol_version"], "time_h": s["time_h"],
                               "compartment": s["compartment"], "extraction_protocol_version": s["extraction_protocol_version"]})
    payload.update(changes)
    return payload
