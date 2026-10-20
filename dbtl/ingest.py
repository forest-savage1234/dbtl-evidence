"""CSV peak-area adapter v1. Exact version references prevent head drift."""
import csv
from pathlib import Path

from .core import IntegrityError, digest, identifier

ADAPTER_ID = "peak-area-csv:1"
FIELDS = ["measurement_id", "sample_version", "calibration_version", "analyte_id",
          "response", "response_unit", "dilution", "qc", "technical_replicate_id", "run_id"]


def ingest_csv(db, source, *, actor="local-operator", max_rows=100000):
    """All registry rows commit together. Failed imports may leave unreferenced objects."""
    raw = db.objects.add(source)
    adapter = db.objects.add(Path(__file__))
    import_id = "import:" + digest({"raw": raw, "adapter": adapter, "id": ADAPTER_ID})
    with db.atomic():
        existing = db.conn.execute("SELECT id FROM heads WHERE entity_id=?", (import_id,)).fetchone()
        if existing:
            record = db.get(existing[0])
            versions = [r[0] for r in db.conn.execute("SELECT dependent_id FROM edges WHERE source_id=? AND role='raw' ORDER BY dependent_id", (record["id"],))]
            return {"import_version": record["id"], "measurement_versions": versions,
                    "rows": len(versions), "reused": True}
        imported = db.capture(import_id, "import", {"source_digest": raw, "source_name": Path(source).name,
                              "adapter_id": ADAPTER_ID, "adapter_sha256": adapter},
                              artifacts=[raw, adapter], actor=actor)
        versions, seen = [], set()
        try:
            with db.objects.verify(raw).open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                if reader.fieldnames != FIELDS:
                    raise IntegrityError("CSV header must exactly match the documented adapter contract")
                for index, row in enumerate(reader, 1):
                    if index > max_rows:
                        raise IntegrityError(f"Import exceeds configured limit of {max_rows} measurements")
                    if None in row or any(v is None or v != v.strip() for v in row.values()):
                        raise IntegrityError(f"CSV row {index}: malformed width or surrounding whitespace")
                    measurement_id = identifier(row.pop("measurement_id"))
                    key = (row["sample_version"], row["analyte_id"], row["run_id"], row["technical_replicate_id"])
                    if key in seen:
                        raise IntegrityError(f"CSV row {index}: duplicate technical acquisition identity")
                    seen.add(key)
                    row["import_version"] = imported["id"]
                    row["source_row"] = index + 1
                    measurement = db.capture(measurement_id, "measurement", row, actor=actor)
                    versions.append(measurement["id"])
        except (UnicodeError, csv.Error) as exc:
            raise IntegrityError("CSV must be well-formed UTF-8") from exc
        if not versions:
            raise IntegrityError("Empty imports are not accepted")
        return {"import_version": imported["id"], "measurement_versions": versions,
                "rows": len(versions), "reused": False}
