"""Independent reviewer assessments. No aggregate scientific-verification flag."""
from .core import IntegrityError
from .graph import outdated_sources, verify_closure

DIMENSIONS = ("arithmetic", "measurement", "sample_identity", "replicate_independence",
              "comparability", "publication_version")
STATUSES = frozenset({"supported", "conflict", "open", "out_of_scope"})


def assessment_dependencies(payload):
    result = [{"role": "subject", "version_id": payload["subject_version"]}] if "subject_version" in payload else []
    dimensions = payload.get("dimensions", {})
    if isinstance(dimensions, dict):
        versions = {v for item in dimensions.values() if isinstance(item, dict)
                    for v in item.get("evidence_versions", []) if isinstance(v, str)}
        result += [{"role": "evidence", "version_id": v} for v in sorted(versions)]
    return result


def validate_assessment(db, payload, deps, artifacts):
    if set(payload) != {"subject_version", "criteria_id", "dimensions"}:
        raise IntegrityError("Assessment requires subject, criteria and separate dimensions only")
    if not isinstance(payload["criteria_id"], str) or not payload["criteria_id"].strip():
        raise IntegrityError("Versioned assessment criteria are required")
    dimensions = payload["dimensions"]
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise IntegrityError("All six independent assessment dimensions are required")
    for item in dimensions.values():
        if not isinstance(item, dict) or set(item) != {"status", "basis", "evidence_versions"}:
            raise IntegrityError("Dimension requires status, basis and evidence_versions")
        if item["status"] not in STATUSES or not isinstance(item["basis"], str) or not item["basis"].strip():
            raise IntegrityError("Invalid assessment status or missing basis")
        values = item["evidence_versions"]
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values) or len(values) != len(set(values)):
            raise IntegrityError("Evidence versions must be a unique list")
        if item["status"] == "supported" and not values and not artifacts:
            raise IntegrityError("Supported assessment needs retained evidence; still a reviewer assertion")
    if deps != sorted(assessment_dependencies(payload), key=lambda d: (d["role"], d["version_id"])):
        raise IntegrityError("Assessment dependencies do not match declared evidence")


def assess(db, entity_id, subject_version, dimensions, *, criteria_id, **kwargs):
    return db.capture(entity_id, "assessment", {"subject_version": subject_version,
                      "criteria_id": criteria_id, "dimensions": dimensions}, **kwargs)


def summary(db, subject_version):
    db.get(subject_version)
    records = [r for r in db.versions("assessment", heads_only=True)
               if r["payload"]["subject_version"] == subject_version]
    for r in records:
        verify_closure(db, r["id"])
    stale = any(outdated_sources(db, r["id"]) for r in records)
    result = {}
    for dimension in DIMENSIONS:
        states = [r["payload"]["dimensions"][dimension]["status"] for r in records]
        status = ("conflict" if "conflict" in states else "open" if stale or not states or "open" in states
                  or len(set(states)) > 1 else states[0])
        result[dimension] = {"status": status, "assessment_versions": [r["id"] for r in records]}
    return {"subject_version": subject_version, "dimensions": result, "stale_evidence": bool(stale),
            "meaning": "Scoped reviewer assessments; not independently authenticated scientific truth."}
