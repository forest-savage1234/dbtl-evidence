"""CSV peak-area adapter v1. Exact version references prevent head drift."""
import csv
import json
from pathlib import Path

from .core import IntegrityError, digest, identifier

ADAPTER_ID = "peak-area-csv:2"
FIELDS = ["measurement_id", "sample_version", "calibration_version", "analyte_id",
          "response", "response_unit", "dilution", "qc", "quantification", "technical_replicate_id", "run_id"]


def ingest_csv(db, source, *, actor="local-operator", max_rows=100000):
    """All registry rows commit together. Failed imports may leave unreferenced objects."""
    raw = db.objects.add(source)
    adapter = db.objects.add(Path(__file__))
    import_id = "import:" + digest({"raw": raw, "adapter": adapter, "id": ADAPTER_ID})
    with db.atomic():
        existing = db.conn.execute("SELECT id FROM heads WHERE entity_id=?", (import_id,)).fetchone()
        if existing:
            record = db.get(existing[0])
            versions = [r[0] for r in db.conn.execute("""SELECT v.id FROM versions v JOIN edges e ON e.dependent_id=v.id
                WHERE e.source_id=? AND e.role='raw' AND v.revision=1
                ORDER BY CAST(json_extract(v.record,'$.payload.source_row') AS INTEGER)""", (record["id"],))]
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


def verify_raw_binding(db, entity_id, payload, *, initial=None):
    """Verify the claimed source row, including raw signal and acquisition identity.

    Cache parsing, never an integrity verdict: datasets rehash their full artifact
    closure before calculation. Revisions may change calibration, sample mapping,
    QC, or censoring interpretation with a preserved predecessor and reason.
    Changing a raw signal requires a newly retained source file with that signal.
    """
    imported = db.get(payload["import_version"])
    p = imported["payload"]
    if p["adapter_id"] != ADAPTER_ID:
        raise IntegrityError("Unsupported raw adapter; use the recorded compatible implementation")
    source_row = payload.get("source_row")
    if type(source_row) is not int or source_row < 2:
        raise IntegrityError("A measurement must identify its exact source row")
    cache = getattr(db, "_raw_row_cache", {})
    db._raw_row_cache = cache
    key = p["source_digest"]
    if key not in cache:
        try:
            with db.objects.verify(key).open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, strict=True)
                if reader.fieldnames != FIELDS:
                    raise IntegrityError("Retained raw file has an incompatible CSV contract")
                values = []
                for row in reader:
                    if len(values) >= 100000:
                        raise IntegrityError("Raw binding exceeds the v1 limit of 100000 measurements")
                    values.append(row)
        except (UnicodeError, csv.Error) as exc:
            raise IntegrityError("Retained source is not well-formed UTF-8 CSV") from exc
        if len(cache) >= 4:
            cache.pop(next(iter(cache)))
        cache[key] = values
    try:
        raw = cache[key][source_row - 2]
    except IndexError as exc:
        raise IntegrityError("Claimed source row does not exist") from exc
    fields = ["analyte_id", "response", "response_unit", "dilution", "technical_replicate_id", "run_id"]
    existing = db.conn.execute("SELECT 1 FROM entities WHERE id=?", (entity_id,)).fetchone()
    if initial is True or (initial is None and existing is None):
        fields += ["sample_version", "calibration_version", "qc", "quantification"]
    if raw.get("measurement_id") != entity_id or any(raw.get(field) != payload.get(field) for field in fields):
        raise IntegrityError("Measurement does not match its retained source row")
