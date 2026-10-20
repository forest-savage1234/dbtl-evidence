import csv
from pathlib import Path

from dbtl.ingest import FIELDS


def setup_assay(db, prefix="A", strain=None, culture=None, calibration=None, **context):
    protocol = db.put("protocol:" + prefix, "protocol", {"name": "synthetic culture protocol"})
    extraction = db.put("extraction:" + prefix, "protocol", {"name": "synthetic extraction"})
    strain = strain or db.put("strain:" + prefix, "strain", {"genotype_status": "unverified"})
    culture_payload = {"strain_version": strain["id"], "protocol_version": protocol["id"],
                       "medium": "defined-medium:1", "temperature_c": "30", "ph": "7",
                       "oxygenation": "shaken-aerobic", "vessel": "flask:250mL", "batch": "batch:1"}
    culture_payload.update(context)
    culture = culture or db.capture("culture:" + prefix, "culture", culture_payload)
    sample = db.capture("sample:" + prefix, "sample", {"culture_version": culture["id"], "time_h": "24",
                        "compartment": "supernatant", "extraction_protocol_version": extraction["id"]})
    calibration = calibration or db.capture("calibration:" + prefix, "calibration", {
        "analyte_id": "CHEBI:synthetic-product", "response_unit": "area", "concentration_unit": "mg/L",
        "slope": "2", "intercept": "10", "min_response": "10", "max_response": "10000"})
    return {"protocol": protocol, "extraction": extraction, "strain": strain,
            "culture": culture, "sample": sample, "calibration": calibration}


def write_csv(path, parts, *, response="1010", rows=None, run="run:1"):
    base = {"measurement_id": "measurement:" + parts["sample"]["entity_id"].split(":")[-1],
            "sample_version": parts["sample"]["id"], "calibration_version": parts["calibration"]["id"],
            "analyte_id": "CHEBI:synthetic-product", "response": response, "response_unit": "area",
            "dilution": "1", "qc": "pass", "technical_replicate_id": "tech:1", "run_id": run}
    rows = rows if rows is not None else [base]
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return base
