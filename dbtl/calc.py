"""Descriptive product-titer comparison. No causal or significance inference.

Linear calibration convention: response = slope * concentration + intercept.
Dilution is a multiplicative correction to the culture concentration. Analytical
validation, calibration fitting, and uncertainty propagation are outside v1.0.
"""
from collections import defaultdict
from decimal import Decimal, localcontext, ROUND_HALF_EVEN

from .core import IntegrityError
from .domain import number
from .graph import outdated_sources, verify_closure

ALGORITHM_ID = "linear-titer-comparison:1"
FACTORS = {"g/L": Decimal(1), "mg/L": Decimal("0.001"), "ug/L": Decimal("0.000001")}


def decimal_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def titer(db, measurement):
    m = measurement["payload"]
    c = db.get(m["calibration_version"])["payload"]
    response = number(m["response"])
    if m["quantification"] != "quantified":
        raise IntegrityError("quantification:" + m["quantification"])
    if not number(c["min_response"]) <= response <= number(c["max_response"]):
        raise IntegrityError("outside_declared_calibration_range")
    with localcontext() as ctx:
        ctx.prec = 50
        ctx.rounding = ROUND_HALF_EVEN
        value = ((response - number(c["intercept"])) / number(c["slope"])) * number(m["dilution"]) * FACTORS[c["concentration_unit"]]
        if value < 0:
            raise IntegrityError("negative_calculated_concentration")
        return value


def evaluate(db, cohort_version, policy_version, *, historical=False):
    cohort, policy = db.get(cohort_version), db.get(policy_version)
    if cohort["kind"] != "cohort" or policy["kind"] != "policy":
        raise IntegrityError("Comparison requires exact cohort and policy versions")
    verify_closure(db, cohort_version)
    verify_closure(db, policy_version)
    if not historical and (outdated_sources(db, cohort_version) or outdated_sources(db, policy_version)):
        raise IntegrityError("Current comparison has superseded evidence; reconcile it explicitly")
    p = policy["payload"]
    included, excluded = [], []
    groups = defaultdict(list)
    for version_id in sorted(cohort["payload"]["measurement_versions"]):
        measurement = db.get(version_id)
        m = measurement["payload"]
        sample = db.get(m["sample_version"])
        s = sample["payload"]
        culture = db.get(s["culture_version"])
        c = culture["payload"]
        strain = db.get(c["strain_version"])
        context = {k: c.get(k) for k in ("medium", "temperature_c", "ph", "oxygenation", "vessel", "batch")}
        context.update({"culture_protocol_version": c["protocol_version"], "time_h": s.get("time_h"),
                        "compartment": s.get("compartment"), "extraction_protocol_version": s["extraction_protocol_version"]})
        reasons = []
        if m["qc"] != "pass":
            reasons.append("qc:" + m["qc"])
        if m["analyte_id"] != p["analyte_id"]:
            reasons.append("analyte_mismatch")
        if p["genotype_requirement"] == "asserted_verified" and strain["payload"].get("genotype_status") != "asserted_verified":
            reasons.append("genotype_evidence_not_asserted_verified")
        for field, expected in sorted(p["context"].items()):
            actual = context[field]
            if actual is None or actual == "":
                reasons.append("missing_context:" + field)
            elif field in {"temperature_c", "ph", "time_h"}:
                if number(actual) != number(expected):
                    reasons.append("context_mismatch:" + field)
            elif actual != expected:
                reasons.append("context_mismatch:" + field)
        try:
            value = titer(db, measurement)
        except IntegrityError as exc:
            reasons.append(str(exc))
        if reasons:
            excluded.append({"measurement_version": version_id, "reasons": sorted(reasons)})
            continue
        row = {"measurement_version": version_id, "strain_version": strain["id"], "strain_id": strain["entity_id"],
               "culture_id": culture["entity_id"], "sample_id": sample["entity_id"], "titer_g_l": decimal_text(value)}
        included.append(row)
        groups[(strain["id"], culture["entity_id"])].append(value)
    with localcontext() as ctx:
        ctx.prec = 50
        ctx.rounding = ROUND_HALF_EVEN
        biological = defaultdict(list)
        for (strain, culture), values in sorted(groups.items()):
            biological[strain].append({"culture_id": culture, "technical_n": len(values),
                                       "mean_g_l": decimal_text(sum(values) / len(values))})
        summaries = []
        for strain, cultures in sorted(biological.items()):
            means = [number(c["mean_g_l"]) for c in cultures]
            mean = sum(means) / len(means)
            sd = (sum((x - mean)**2 for x in means) / (len(means) - 1)).sqrt() if len(means) > 1 else None
            summaries.append({"strain_version": strain, "strain_id": db.get(strain)["entity_id"],
                              "biological_n": len(means), "cultures": cultures, "mean_g_l": decimal_text(mean),
                              "sample_sd_g_l": decimal_text(sd) if sd is not None else None,
                              "eligible_for_descriptive_ranking": len(means) >= p["min_biological_replicates"]})
        eligible = [s for s in summaries if s["eligible_for_descriptive_ranking"]]
        for summary in eligible:
            summary["rank"] = 1 + sum(number(other["mean_g_l"]) > number(summary["mean_g_l"]) for other in eligible)
    return {"algorithm_id": ALGORITHM_ID, "cohort_version": cohort_version, "policy_version": policy_version,
            "metric": "titer_g_l", "included": included, "excluded": excluded,
            "summaries": sorted(summaries, key=lambda s: (s.get("rank", 10**9), s["strain_id"])),
            "interpretation": "Descriptive ranking under declared context; no significance, causal effect, or yield claim."}
