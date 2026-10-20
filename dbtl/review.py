"""Correction impact and explicit human dispositions; never automatic truth."""
from .core import IntegrityError, digest
from .graph import closure, impact, outdated_sources

REVIEWED_KINDS = frozenset({"dataset", "decision", "model"})


def finding_key(target, old, current):
    return digest({"target": target, "old": old, "current": current})


def findings(db, *, include_acknowledged=False):
    result = []
    reviews = {r["payload"]["finding_id"]: r for r in db.versions("review", heads_only=True)}
    path_cache = {}
    for target in db.versions(heads_only=True):
        if target["kind"] not in REVIEWED_KINDS:
            continue
        for source in outdated_sources(db, target["id"]):
            old, current = source["old"], source["current"]
            key = finding_key(target["id"], old, current)
            review = reviews.get(key)
            if review and not include_acknowledged:
                continue
            if old not in path_cache:
                path_cache[old] = {x["record"]["id"]: x["path"] for x in impact(db, old)}
            result.append({"finding_id": key, "target_version": target["id"], "target_entity": target["entity_id"],
                           "target_kind": target["kind"], "source_old": old, "source_current": current,
                           "source_entity": source["entity_id"], "path": path_cache[old][target["id"]],
                           "acknowledged": review is not None,
                           "disposition": review["payload"]["disposition"] if review else None,
                           "meaning": "Evidence changed; reassessment is required, not automatic rejection."})
    return sorted(result, key=lambda f: (f["target_entity"], f["source_entity"], f["finding_id"]))


def validate_review(db, payload):
    old, current = db.get(payload["source_old"]), db.get(payload["source_current"])
    target = db.get(payload["target_version"])
    if target["kind"] not in REVIEWED_KINDS:
        raise IntegrityError("Only declared derived outputs can receive review dispositions")
    if old["entity_id"] != current["entity_id"] or current["revision"] <= old["revision"]:
        raise IntegrityError("Review must link an actual source revision")
    if db.latest(current["entity_id"])["id"] != current["id"]:
        raise IntegrityError("Review source changed again; assess the current version")
    if old["id"] not in {r["id"] for r in closure(db, target["id"])}:
        raise IntegrityError("Review target did not depend on the changed evidence")
    if payload.get("finding_id") != finding_key(target["id"], old["id"], current["id"]):
        raise IntegrityError("Finding identity does not match the affected versions")
    if payload.get("disposition") not in {"retain_historical", "retire"}:
        raise IntegrityError("Supported dispositions are retain_historical and retire")
    if not isinstance(payload.get("note"), str) or not payload["note"].strip():
        raise IntegrityError("A substantive human review note is required")


def acknowledge(db, finding_id, *, disposition, note, actor):
    with db.atomic():
        finding = next((f for f in findings(db) if f["finding_id"] == finding_id), None)
        if not finding:
            raise IntegrityError("Finding is no longer pending; refresh the review queue")
        payload = {k: finding[k] for k in ("finding_id", "target_version", "source_old", "source_current")}
        payload.update({"disposition": disposition, "note": note})
        return db.capture("review:" + finding_id, "review", payload, actor=actor, reason="human review disposition")


def recalibrate(db, measurement_version, calibration_version, *, actor, reason):
    with db.atomic():
        measurement, calibration = db.get(measurement_version), db.get(calibration_version)
        if measurement["kind"] != "measurement" or calibration["kind"] != "calibration":
            raise IntegrityError("Explicit measurement and calibration versions required")
        old_calibration = db.get(measurement["payload"]["calibration_version"])
        if old_calibration["entity_id"] != calibration["entity_id"]:
            raise IntegrityError("Calibration correction must revise the same declared calibration entity")
        if db.latest(calibration["entity_id"])["id"] != calibration_version:
            raise IntegrityError("Choose the current calibration version explicitly")
        return db.capture(measurement["entity_id"], "measurement", {**measurement["payload"], "calibration_version": calibration_version},
                          expected=measurement_version, actor=actor, reason=reason)


def refresh_cohort(db, cohort_version, *, actor, reason):
    """Advance existing members to their heads. Never add independent new results implicitly."""
    with db.atomic():
        cohort = db.get(cohort_version)
        if cohort["kind"] != "cohort":
            raise IntegrityError("Expected a cohort version")
        members = [db.latest(db.get(v)["entity_id"])["id"] for v in cohort["payload"]["measurement_versions"]]
        if members == cohort["payload"]["measurement_versions"]:
            raise IntegrityError("No cohort members have changed")
        return db.capture(cohort["entity_id"], "cohort", {**cohort["payload"], "measurement_versions": members},
                          expected=cohort_version, actor=actor, reason=reason)
