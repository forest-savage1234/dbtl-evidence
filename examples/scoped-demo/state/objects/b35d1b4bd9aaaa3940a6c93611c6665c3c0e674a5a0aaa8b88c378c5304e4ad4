"""Structural audit plus explicitly separate historical numerical replay status."""
from collections import defaultdict
import json
import re
import sqlite3

from .core import IntegrityError, SCHEMA


def normalized(sql):
    return re.sub(r"\s+", " ", sql.lower().replace("if not exists ", "")).strip().rstrip(";")


def audit(db):
    errors, warnings, records, artifact_keys = [], [], {}, set()
    replayed, replay_blocked, packets_replayed, packets_blocked = 0, 0, 0, 0
    try:
        quick = [r[0] for r in db.conn.execute("PRAGMA quick_check")]
        if quick != ["ok"]:
            errors.extend(quick)
        if list(db.conn.execute("PRAGMA foreign_key_check")):
            errors.append("Foreign-key violations")
        expected = {}
        for pattern in [r"CREATE TRIGGER IF NOT EXISTS (\w+).*?END;", r"CREATE VIEW IF NOT EXISTS (\w+).*?;"]:
            for match in re.finditer(pattern, SCHEMA, flags=re.S):
                expected[match.group(1)] = normalized(match.group(0))
        for name, sql in expected.items():
            row = db.conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()
            if row is None or normalized(row[0]) != sql:
                errors.append("Missing or altered immutable registry structure: " + name)
        entities = dict(db.conn.execute("SELECT id,kind FROM entities"))
        order = {}
        grouped = defaultdict(list)
        for row in db.conn.execute("SELECT rowid,id FROM versions ORDER BY rowid"):
            try:
                record = db.get(row["id"])
                if record.get("schema") != 1 or entities.get(record["entity_id"]) != record["kind"]:
                    raise IntegrityError("Record schema or entity kind mismatch: " + record["id"])
                if not isinstance(record.get("payload"), dict) or not isinstance(record.get("dependencies"), list) or not isinstance(record.get("artifacts"), list):
                    raise IntegrityError("Malformed immutable record: " + record["id"])
                for dep in record["dependencies"]:
                    if dep["version_id"] not in records:
                        raise IntegrityError("Dependency is missing or not an earlier version: " + record["id"])
                for key in record["artifacts"]:
                    if key not in artifact_keys:
                        db.objects.verify(key)
                        artifact_keys.add(key)
                if record["kind"] == "measurement":
                    from .ingest import verify_raw_binding
                    verify_raw_binding(db, record["entity_id"], record["payload"], initial=record["revision"] == 1)
                records[record["id"]] = record
                order[record["id"]] = row["rowid"]
                grouped[record["entity_id"]].append(record)
            except (IntegrityError, KeyError, TypeError, ValueError) as exc:
                errors.append(str(exc))
        for entity, values in grouped.items():
            previous = None
            for revision, record in enumerate(values, 1):
                if record["revision"] != revision or record["previous_id"] != previous:
                    errors.append("Broken revision chain: " + entity)
                previous = record["id"]
        for entity in entities:
            if entity not in grouped:
                errors.append("Entity has no valid version: " + entity)
        if not errors:
            from .datasets import source_manifest, replay
            current_manifest = source_manifest()
            for record in records.values():
                if record["kind"] == "dataset":
                    if record["payload"].get("algorithm_manifest") != current_manifest:
                        replay_blocked += 1
                        warnings.append("Historical replay requires a different recorded implementation/runtime: " + record["id"])
                    else:
                        try:
                            replay(db, record["id"])
                            replayed += 1
                        except (IntegrityError, KeyError, ValueError) as exc:
                            errors.append("Numerical replay failed: " + str(exc))
                elif record["kind"] == "packet":
                    if record["payload"].get("algorithm_manifest") != current_manifest:
                        packets_blocked += 1
                        warnings.append("Packet replay requires recorded source/runtime: "+record["id"])
                    else:
                        try:
                            from .packets import replay as packet_replay
                            packet_replay(db,record["id"]);packets_replayed += 1
                        except (IntegrityError,KeyError,ValueError) as exc: errors.append("Packet replay failed: "+str(exc))
                elif record["kind"] in {"pool_snapshot","quantity_result","uncertainty_result","literature_evidence"}:
                    try:
                        kind=record["kind"]
                        if kind=="pool_snapshot":
                            from .pools import replay_snapshot
                            replay_snapshot(db,record["id"])
                        elif kind=="quantity_result":
                            from .quantities import replay_result
                            replay_result(db,record["id"])
                        elif kind=="uncertainty_result":
                            from .uncertainty import validate_assay
                            validate_assay(db,kind,record["payload"],record["dependencies"],record["artifacts"])
                        else:
                            from .handoff import validate_handoff
                            validate_handoff(db,record["payload"],record["dependencies"],record["artifacts"])
                    except (IntegrityError,KeyError,TypeError,ValueError) as exc:errors.append("Evidence reconstruction failed: "+str(exc))
        objects = [p for p in db.objects.root.iterdir() if re.fullmatch(r"[0-9a-f]{64}", p.name)]
        orphans = len([p for p in objects if p.name not in artifact_keys])
        if orphans:
            warnings.append(f"{orphans} unreferenced artifact(s); retained safely after capture/rollback, not automatically deleted")
        return {"ok": not errors, "meaning": "Local registry/byte consistency; not scientific validity or authenticated provenance",
                "version_count": db.conn.execute("SELECT count(*) FROM versions").fetchone()[0],
                "artifact_count": len(artifact_keys), "unreferenced_artifacts": orphans,
                "datasets_replayed": replayed, "datasets_replay_blocked": replay_blocked,
                "packets_replayed": packets_replayed, "packets_replay_blocked": packets_blocked,
                "warnings": warnings, "errors": errors}
    except (sqlite3.Error, OSError, KeyError, TypeError, ValueError) as exc:
        return {"ok": False, "version_count": len(records), "artifact_count": len(artifact_keys),
                "errors": [*errors, "Audit could not complete: " + str(exc)], "warnings": warnings}
