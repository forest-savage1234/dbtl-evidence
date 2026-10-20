"""Small versioned contracts; absent scientific context is never invented."""
from decimal import Decimal, InvalidOperation
import re

from .core import IntegrityError, identifier


REFS = {
    "culture": {"strain_version": ("strain", "strain"), "protocol_version": ("protocol", "protocol")},
    "sample": {"culture_version": ("culture", "culture"),
               "extraction_protocol_version": ("extraction_protocol", "protocol")},
    "measurement": {"sample_version": ("sample", "sample"),
                    "calibration_version": ("calibration", "calibration"),
                    "import_version": ("raw", "import")},
    "decision": {"dataset_version": ("dataset", "dataset")},
    "dataset": {"cohort_version": ("cohort", "cohort"), "policy_version": ("policy", "policy")},
    "review": {"target_version": ("review_target", None), "source_old": ("source_old", None),
               "source_current": ("source_current", None)},
}

CONTEXT_FIELDS = frozenset({"medium", "temperature_c", "ph", "oxygenation", "vessel",
                            "batch", "culture_protocol_version", "time_h", "compartment",
                            "extraction_protocol_version"})


def number(value, field="number") -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise IntegrityError(f"{field}: supply a decimal string or integer, never a float")
    text = str(value)
    if len(text) > 128 or not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
        raise IntegrityError(f"{field}: invalid finite decimal")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise IntegrityError(f"{field}: invalid decimal") from exc
    if not value.is_finite() or abs(value.as_tuple().exponent) > 300 or abs(value.adjusted()) > 300:
        raise IntegrityError(f"{field}: decimal magnitude is outside the supported range")
    return value


def text(payload, field):
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise IntegrityError(f"{field}: nonempty text required")
    return value


def dependencies(kind: str, payload: dict) -> list[dict]:
    if kind in {"trajectory", "process_policy"}:
        from .process import process_dependencies
        return process_dependencies(kind, payload)
    if kind in {"assay_profile", "uncertainty_result"}:
        from .uncertainty import assay_dependencies
        return assay_dependencies(kind, payload)
    if kind == "genotype_observation":
        from .genotypes import genotype_dependencies
        return genotype_dependencies(payload)
    if kind in {"experimental_unit", "unit_assignment"}:
        from .units import unit_dependencies
        return unit_dependencies(kind, payload)
    if kind in {"quantity", "quantity_result"}:
        from .quantities import quantity_dependencies
        return quantity_dependencies(kind, payload)
    if kind in {"availability", "watch", "watch_review"}:
        from .watches import watch_dependencies
        return watch_dependencies(kind, payload)
    if kind in {"pool", "pool_snapshot"}:
        from .pools import pool_dependencies
        return pool_dependencies(kind, payload)
    if kind == "assessment":
        from .assessments import assessment_dependencies
        return assessment_dependencies(payload)
    result = [{"role": role, "version_id": payload[field]}
              for field, (role, _) in REFS.get(kind, {}).items() if field in payload]
    if kind == "cohort":
        result += [{"role": "candidate", "version_id": v} for v in payload.get("measurement_versions", [])]
    if kind == "policy":
        context = payload.get("context", {})
        if isinstance(context, dict):
            result += [{"role": role, "version_id": context[field]} for field, role in
                       [("culture_protocol_version", "culture_protocol"), ("extraction_protocol_version", "extraction_protocol")]
                       if field in context]
    return result


def validate(db, kind, payload, deps, artifacts, entity_id):
    if kind in {"trajectory", "process_policy"}:
        from .process import validate_process
        validate_process(db, kind, payload, deps, artifacts)
    if kind in {"assay_profile", "uncertainty_result"}:
        from .uncertainty import validate_assay
        validate_assay(db, kind, payload, deps, artifacts)
    if kind == "genotype_observation":
        from .genotypes import validate_genotype
        validate_genotype(db, payload, deps, artifacts)
    if kind in {"experimental_unit", "unit_assignment"}:
        from .units import validate_unit_record
        validate_unit_record(db, kind, payload, deps, entity_id)
    if kind in {"quantity", "quantity_result"}:
        from .quantities import validate_quantity_record
        validate_quantity_record(db, kind, payload, deps, artifacts)
    if kind in {"availability", "watch", "watch_review"}:
        from .watches import validate_watch_record
        validate_watch_record(db, kind, payload, deps)
    if kind in {"pool", "pool_snapshot"}:
        from .pools import validate_pool_record
        validate_pool_record(db, kind, payload, deps)
    if kind == "assessment":
        from .assessments import validate_assessment
        validate_assessment(db, payload, deps, artifacts)
    pairs = {(d["role"], d["version_id"]) for d in deps}
    for field, (role, required_kind) in REFS.get(kind, {}).items():
        version_id = payload.get(field)
        if not isinstance(version_id, str) or (role, version_id) not in pairs:
            raise IntegrityError(f"{kind}.{field}: exact typed dependency required")
        if required_kind is not None and db.get(version_id)["kind"] != required_kind:
            raise IntegrityError(f"{kind}.{field}: requires {required_kind}")
    if "extensions" in payload:
        if not isinstance(payload["extensions"], dict) or any(":" not in k for k in payload["extensions"]):
            raise IntegrityError("Extension keys must be namespaced, e.g. lab:editor")
    if kind == "strain":
        if payload.get("genotype_status", "unverified") not in {"unverified", "asserted_verified"}:
            raise IntegrityError("Genotype verification is an operator assertion")
        if payload.get("genotype_status") == "asserted_verified" and not artifacts:
            raise IntegrityError("An asserted verified genotype needs an evidence artifact")
    if kind == "culture":
        for field in ("temperature_c", "ph"):
            if field in payload:
                value = number(payload[field], field)
                if field == "ph" and not 0 <= value <= 14:
                    raise IntegrityError("pH outside supported range 0–14")
    if kind == "sample" and "time_h" in payload and number(payload["time_h"], "time_h") < 0:
        raise IntegrityError("Sampling time must be nonnegative")
    if kind == "calibration":
        identifier(text(payload, "analyte_id"))
        if text(payload, "response_unit") != "area":
            raise IntegrityError("v1 adapter supports integrated peak area only")
        if text(payload, "concentration_unit") not in {"g/L", "mg/L", "ug/L"}:
            raise IntegrityError("Unsupported concentration unit")
        if number(payload.get("slope"), "slope") <= 0:
            raise IntegrityError("Calibration slope must be positive")
        number(payload.get("intercept"), "intercept")
        low = number(payload.get("min_response"), "min_response")
        high = number(payload.get("max_response"), "max_response")
        if high <= low:
            raise IntegrityError("Calibration response range must increase")
    if kind == "measurement":
        from .ingest import verify_raw_binding
        verify_raw_binding(db, entity_id, payload)
        identifier(text(payload, "analyte_id"))
        number(payload.get("response"), "response")
        if number(payload.get("dilution"), "dilution") <= 0:
            raise IntegrityError("Dilution must be positive")
        if payload.get("qc") not in {"pass", "fail", "unreviewed"}:
            raise IntegrityError("QC must be pass, fail, or unreviewed")
        if payload.get("quantification") not in {"quantified", "below_loq", "above_uloq", "unreviewed"}:
            raise IntegrityError("An explicit quantification status is required")
        for field in ("technical_replicate_id", "run_id"):
            identifier(text(payload, field))
        text(payload, "response_unit")
        calibration = db.get(payload["calibration_version"])["payload"]
        if (payload["analyte_id"], payload["response_unit"]) != (calibration["analyte_id"], calibration["response_unit"]):
            raise IntegrityError("Measurement and calibration analyte/unit mismatch")
        sample_entity = db.get(payload["sample_version"])["entity_id"]
        duplicate = db.conn.execute("""
            SELECT entity_id FROM versions
            WHERE json_extract(record,'$.kind')='measurement'
              AND json_extract(record,'$.payload.sample_version') IN
                  (SELECT id FROM versions WHERE entity_id=?)
              AND json_extract(record,'$.payload.analyte_id')=?
              AND json_extract(record,'$.payload.run_id')=?
              AND json_extract(record,'$.payload.technical_replicate_id')=?
              AND entity_id<>? LIMIT 1
            """, (sample_entity, payload["analyte_id"], payload["run_id"],
                  payload["technical_replicate_id"], entity_id)).fetchone()
        if duplicate:
            raise IntegrityError("Acquisition identity already belongs to another measurement entity")
    if kind == "activity":
        text(payload, "operation")
        allowed = {"recipient": {"strain"}, "donor": {"strain", "design"},
                   "vector": {"design"}, "protocol": {"protocol"}, "evidence": set()}
        recipients = [d for d in deps if d["role"] == "recipient"]
        if len(recipients) != 1:
            raise IntegrityError("A construction activity must declare exactly one recipient strain")
        for d in deps:
            if d["role"] not in allowed:
                raise IntegrityError("Unknown construction input role")
            if allowed[d["role"]] and db.get(d["version_id"])["kind"] not in allowed[d["role"]]:
                raise IntegrityError("Construction input has the wrong biological role")
    if kind == "strain":
        for d in deps:
            if d["role"] == "built_by" and db.get(d["version_id"])["kind"] != "activity":
                raise IntegrityError("built_by must reference a construction activity")
    if kind == "import":
        for field in ("adapter_id", "adapter_sha256", "source_digest", "source_name"):
            text(payload, field)
        if payload["source_digest"] not in artifacts or payload["adapter_sha256"] not in artifacts:
            raise IntegrityError("Raw bytes and adapter source must both be retained")
    if kind == "cohort":
        values = payload.get("measurement_versions")
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise IntegrityError("Cohort must declare nonempty, unique measurement versions")
        identities = set()
        for v in values:
            record = db.get(v)
            if record["kind"] != "measurement" or ("candidate", v) not in pairs:
                raise IntegrityError("Cohort requires typed measurement dependencies")
            if record["entity_id"] in identities:
                raise IntegrityError("A cohort cannot include two revisions of the same measurement")
            identities.add(record["entity_id"])
    if kind == "decision":
        text(payload, "rationale")
        from .datasets import replay
        from .graph import outdated_sources
        replay(db, payload["dataset_version"])
        if outdated_sources(db, payload["dataset_version"]):
            raise IntegrityError("A new decision cannot silently reuse superseded evidence")
        selected = payload.get("selected_strain_versions")
        eligible = {s["strain_version"] for s in db.get(payload["dataset_version"])["payload"]["result"]["summaries"]
                    if s["eligible_for_descriptive_ranking"]}
        if not isinstance(selected, list) or not selected or len(selected) != len(set(selected)) or not set(selected) <= eligible:
            raise IntegrityError("Selected strains must be unique, eligible members of the declared dataset")
    if kind == "policy":
        if payload.get("metric") != "titer_g_l":
            raise IntegrityError("Only product titer is implemented; yield/productivity need other denominators")
        identifier(text(payload, "analyte_id"))
        context = payload.get("context")
        if not isinstance(context, dict) or set(context) != CONTEXT_FIELDS:
            raise IntegrityError("Comparison policy must declare exactly the supported context fields")
        for field in CONTEXT_FIELDS:
            text(context, field)
        for field in ("temperature_c", "ph", "time_h"):
            number(context[field], field)
        for field in ("culture_protocol_version", "extraction_protocol_version"):
            if db.get(context[field])["kind"] != "protocol":
                raise IntegrityError("Policy protocol references must identify exact protocol versions")
            role = "culture_protocol" if field == "culture_protocol_version" else "extraction_protocol"
            if (role, context[field]) not in pairs:
                raise IntegrityError("Policy context references must be dependencies")
        if type(payload.get("min_biological_replicates")) is not int or payload["min_biological_replicates"] < 1:
            raise IntegrityError("Minimum biological replicate count must be a positive integer")
        if payload.get("technical_aggregation") != "arithmetic_mean":
            raise IntegrityError("Declare the supported technical aggregation explicitly")
        if payload.get("genotype_requirement") not in {"any", "asserted_verified"}:
            raise IntegrityError("Declare genotype eligibility explicitly")
    if kind == "dataset":
        from .datasets import validate_dataset
        validate_dataset(db, payload, artifacts)
    if kind == "review":
        from .review import validate_review
        validate_review(db, payload)
