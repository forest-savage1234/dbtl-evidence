"""Bounded registry pools with immutable, independently reconstructable snapshots."""
from .core import IntegrityError, digest, identifier
from .graph import verify_closure

FILTERS = frozenset({"analyte_id", "qc", "medium", "batch", "vessel"})


def journal(db, watermark=None):
    maximum = db.conn.execute("SELECT coalesce(max(rowid),0) FROM versions").fetchone()[0]
    watermark = maximum if watermark is None else watermark
    if type(watermark) is not int or not 0 <= watermark <= maximum:
        raise IntegrityError("Invalid registry watermark")
    rows = list(db.conn.execute("SELECT rowid,id,sha256 FROM versions WHERE rowid<=? ORDER BY rowid", (watermark,)))
    records = {r["id"]: db.get(r["id"]) for r in rows}
    heads = {r["entity_id"]: r for r in records.values()}
    return watermark, records, heads, digest([[r["rowid"], r["id"], r["sha256"]] for r in rows])


def pool_dependencies(kind, payload):
    if kind == "pool":
        return []
    return ([{"role": "pool", "version_id": payload["pool_version"]}] if "pool_version" in payload else []) + [
        {"role": "candidate", "version_id": row["measurement_version"]}
        for row in payload.get("candidates", []) if isinstance(row, dict) and "measurement_version" in row]


def validate_pool_record(db, kind, payload, deps):
    if kind == "pool":
        if set(payload) != {"entity_prefix", "filters", "boundary"} or payload["boundary"] != "registered_local_measurements_only":
            raise IntegrityError("Pool needs an explicit bounded local-registry scope")
        identifier(payload["entity_prefix"])
        filters = payload["filters"]
        if not isinstance(filters, dict) or "analyte_id" not in filters or not set(filters) <= FILTERS:
            raise IntegrityError("Unsupported pool predicate; no SQL or executable filters")
        if any(not isinstance(v, str) or not v.strip() for v in filters.values()) or deps:
            raise IntegrityError("Pool predicates require nonempty exact values and no dependencies")
    else:
        if set(payload) != {"pool_version", "watermark", "journal_sha256", "candidates", "algorithm_id", "coverage"}:
            raise IntegrityError("Malformed pool snapshot")
        expected = compute_snapshot(db, payload["pool_version"], payload["watermark"])
        if payload != expected or deps != sorted(pool_dependencies(kind, payload), key=lambda d: (d["role"], d["version_id"])):
            raise IntegrityError("Pool snapshot differs from the recorded registry history")


def compute_snapshot(db, pool_version, watermark=None):
    watermark, records, heads, fingerprint = journal(db, watermark)
    if pool_version not in records or records[pool_version]["kind"] != "pool":
        raise IntegrityError("Pool version is not present at this watermark")
    pool = records[pool_version]["payload"]
    candidates = []
    for measurement in sorted(heads.values(), key=lambda r: r["entity_id"]):
        if measurement["kind"] != "measurement" or not measurement["entity_id"].startswith(pool["entity_prefix"]):
            continue
        m = measurement["payload"]
        sample = records[m["sample_version"]]
        culture = records[sample["payload"]["culture_version"]]
        context = {**culture["payload"], **m}
        missing, mismatched, stale = [], [], []
        for field, expected in sorted(pool["filters"].items()):
            actual = context.get(field)
            if actual is None or actual == "": missing.append("missing:"+field)
            elif actual != expected: mismatched.append("mismatch:"+field)
        stack, seen = [measurement["id"]], set()
        while stack:
            v = stack.pop()
            if v in seen: continue
            seen.add(v)
            r = records[v]
            if heads[r["entity_id"]]["id"] != v: stale.append("superseded:"+r["entity_id"])
            stack.extend(d["version_id"] for d in r["dependencies"])
        reasons = sorted(set(missing+mismatched+stale))
        status = "excluded" if mismatched else "uncertain" if missing or stale else "included"
        candidates.append({"measurement_version": measurement["id"], "entity_id": measurement["entity_id"],
                           "status": status, "reasons": reasons})
    return {"pool_version": pool_version, "watermark": watermark, "journal_sha256": fingerprint,
            "candidates": candidates, "algorithm_id": "bounded-measurement-pool:1",
            "coverage": "registered_history_only; upstream completeness not established"}


def snapshot(db, entity_id, pool_version, **kwargs):
    with db.atomic():
        verify_closure(db, pool_version)
        payload = compute_snapshot(db, pool_version)
        for row in payload["candidates"]:
            verify_closure(db, row["measurement_version"])
        return db.capture(entity_id, "pool_snapshot", payload, **kwargs)


def replay_snapshot(db, snapshot_version):
    r = db.get(snapshot_version)
    if r["kind"] != "pool_snapshot": raise IntegrityError("Expected pool snapshot")
    verify_closure(db, snapshot_version)
    expected = compute_snapshot(db, r["payload"]["pool_version"], r["payload"]["watermark"])
    if expected != r["payload"]: raise IntegrityError("Snapshot history does not reconstruct")
    return {"ok": True, "snapshot_version": snapshot_version, "watermark": expected["watermark"],
            "meaning": "Bounded registry reconstruction, not global evidence completeness."}
