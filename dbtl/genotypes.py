"""Material- and time-scoped genotype observations, never whole-genome verification."""
import json
from datetime import datetime, timezone
from decimal import Decimal

from .core import IntegrityError, identifier
from .domain import number
from .graph import verify_closure, outdated_sources
from .assessments import summary as assessment_summary


def utc(value):
    if not isinstance(value, str): raise IntegrityError("UTC observation time required")
    try: result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise IntegrityError("Invalid observation time") from exc
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise IntegrityError("Observation times must include UTC offset")
    return result.astimezone(timezone.utc)


def genotype_dependencies(p):
    return [{"role": role, "version_id": p[field]} for field, role in
            [("strain_version", "strain"), ("material_version", "material")] if field in p]


def calls(db, source_digest):
    path = db.objects.verify(source_digest)
    if path.stat().st_size > 1024*1024: raise IntegrityError("Genotype calls exceed 1 MiB")
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc: raise IntegrityError("Structured genotype calls required") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "calls"} or data["schema"] != "scoped-genotype-calls/1":
        raise IntegrityError("Unsupported genotype call format; arbitrary notes are not calls")
    rows = data["calls"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000: raise IntegrityError("Bounded nonempty genotype calls required")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"region_id", "expected", "observed", "status"}: raise IntegrityError("Invalid genotype call")
        identifier(row["region_id"])
        if row["region_id"] in seen: raise IntegrityError("Duplicate genotype region")
        seen.add(row["region_id"])
        if not isinstance(row["expected"], str) or not row["expected"].strip() or row["status"] not in {"called", "missing", "unresolved"}:
            raise IntegrityError("Genotype calls need an explicit expectation and call status")
        if row["status"] == "called":
            if not isinstance(row["observed"], str) or not row["observed"].strip(): raise IntegrityError("Called region needs an observation")
        elif row["observed"] is not None: raise IntegrityError("Unresolved calls cannot carry a resolved observation")
    return rows


def validate_genotype(db, p, deps, artifacts):
    if set(p) != {"strain_version", "material_version", "observed_at", "generation", "scope", "method", "source_digest", "limitations"}:
        raise IntegrityError("Genotype observation needs exact material, time, method and evidence scope")
    if deps != sorted(genotype_dependencies(p), key=lambda d: (d["role"], d["version_id"])): raise IntegrityError("Genotype dependencies disagree")
    material = db.get(p["material_version"])
    if material["kind"] == "sample": material = db.get(material["payload"]["culture_version"])
    if material["kind"] != "culture" or material["payload"]["strain_version"] != p["strain_version"]:
        raise IntegrityError("Observation material does not identify the declared strain version")
    utc(p["observed_at"])
    if type(p["generation"]) is not int or p["generation"] < 0: raise IntegrityError("Declared generation must be nonnegative")
    if p["scope"] not in {"clone", "population"}: raise IntegrityError("Declare clone versus population scope")
    for field in ("method", "limitations"):
        if not isinstance(p[field], str) or not p[field].strip(): raise IntegrityError("Method and limitations are required")
    if p["source_digest"] not in artifacts: raise IntegrityError("Retain the structured observation bytes")
    calls(db, p["source_digest"])


def evaluate(db, measurement_version, observation_versions, *, required_regions, as_of, max_age_h,
             minimum_generation=0, required_scope="clone"):
    from .units import ancestry
    material = ancestry(db, measurement_version)
    if db.get(measurement_version)["kind"] != "measurement": raise IntegrityError("Expected measurement")
    strain = db.get(material[-1])["payload"]["strain_version"]
    if not isinstance(required_regions, list) or not required_regions or any(not isinstance(v, str) for v in required_regions) or len(set(required_regions)) != len(required_regions):
        raise IntegrityError("Unique required genotype regions must be explicit")
    if required_scope not in {"clone", "population"} or type(minimum_generation) is not int or minimum_generation < 0:
        raise IntegrityError("Invalid genotype scope requirements")
    age_limit = number(max_age_h)
    if age_limit < 0: raise IntegrityError("Observation age limit must be nonnegative")
    now = utc(as_of); covered = set(); issues = []; used = set(); conflict = False
    if not isinstance(observation_versions, list) or len(set(observation_versions)) != len(observation_versions): raise IntegrityError("Unique observation versions required")
    for version in observation_versions:
        r = db.get(version)
        if r["kind"] != "genotype_observation": raise IntegrityError("Expected genotype observation")
        verify_closure(db, version); p = r["payload"]; used.add(version)
        validate_genotype(db, p, r["dependencies"], r["artifacts"])
        age = Decimal(str((now-utc(p["observed_at"])).total_seconds()))/Decimal(3600)
        reason = ("wrong_material" if p["material_version"] not in material[1:] or p["strain_version"] != strain else
                  "scope_mismatch" if p["scope"] != required_scope else "observation_outside_window" if age < 0 or age > age_limit else
                  "generation_too_early" if p["generation"] < minimum_generation else "superseded_evidence" if outdated_sources(db, version) else None)
        if reason: issues.append({"version": version, "reason": reason}); continue
        review = assessment_summary(db, version)
        for d in ("measurement", "sample_identity"):
            used.update(review["dimensions"][d]["assessment_versions"])
            if review["dimensions"][d]["status"] != "supported": issues.append({"version": version, "reason": "unassessed_"+d})
        for row in calls(db, p["source_digest"]):
            if row["region_id"] not in required_regions: continue
            if row["status"] != "called": issues.append({"version": version, "reason": "unresolved_region:"+row["region_id"]})
            elif row["observed"] != row["expected"]:
                conflict = True; issues.append({"version": version, "reason": "discordant_region:"+row["region_id"]})
            else: covered.add(row["region_id"])
    missing = sorted(set(required_regions)-covered)
    return {"status": "conflict" if conflict else "open" if missing or issues else "supported_for_declared_regions",
            "covered_regions": sorted(covered), "missing_regions": missing, "issues": issues, "evidence_versions": sorted(used),
            "meaning": "Scoped source-call concordance and reviewer assessments; no whole-genome, stability or phenotype guarantee."}
