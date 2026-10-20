"""Bounded realized-process trajectory checks, without interpolation or scale-up claims."""
import csv
import io
from decimal import Decimal, localcontext

from .core import IntegrityError
from .domain import number
from .calc import decimal_text
from .genotypes import utc
from .graph import verify_closure, outdated_sources
from .assessments import summary as assessment_summary

VARIABLES={"ph":"1","dissolved_oxygen":"%air_saturation","temperature":"degC"}
TIME_FACTORS={"h":Decimal(1),"min":Decimal(60),"s":Decimal(3600)}


def process_dependencies(kind,p):
    return [{"role":"culture","version_id":p["culture_version"]}] if kind=="trajectory" and "culture_version" in p else []


def points(db,p):
    path=db.objects.verify(p["source_digest"])
    if path.stat().st_size>4*1024*1024: raise IntegrityError("Trajectory exceeds 4 MiB")
    try:
        reader=csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig")),strict=True)
        if reader.fieldnames!=["time","value"]: raise IntegrityError("Trajectory requires exactly time,value columns")
        result=[]
        with localcontext() as ctx:
            ctx.prec=50
            for row in reader:
                if len(result)>=10000 or None in row or any(v is None for v in row.values()): raise IntegrityError("Malformed or unbounded trajectory")
                t=number(row["time"])/TIME_FACTORS[p["time_unit"]];v=number(row["value"])
                if t<0 or result and t<=result[-1][0]: raise IntegrityError("Trajectory times must be nonnegative and strictly increase")
                if p["variable"]=="ph" and not 0<=v<=14: raise IntegrityError("Invalid pH trajectory")
                if p["variable"]=="dissolved_oxygen" and v<0: raise IntegrityError("Negative dissolved oxygen")
                result.append((t,v))
    except (UnicodeError,csv.Error,KeyError) as exc: raise IntegrityError("Malformed trajectory CSV") from exc
    if len(result)<2: raise IntegrityError("At least two realized observations required")
    return result


def validate_process(db,kind,p,deps,artifacts):
    if deps!=process_dependencies(kind,p): raise IntegrityError("Process dependencies disagree")
    if not isinstance(p.get("basis"),str) or not p["basis"].strip(): raise IntegrityError("Process scope needs a basis")
    if kind=="process_policy":
        if set(p)!={"start_h","end_h","max_gap_h","variables","basis"}: raise IntegrityError("Invalid process policy")
        if number(p["start_h"])<0 or number(p["end_h"])<=number(p["start_h"]) or number(p["max_gap_h"])<=0:
            raise IntegrityError("Process window and maximum gap must be explicit and increasing")
        if not isinstance(p["variables"],dict) or not p["variables"] or not set(p["variables"])<=set(VARIABLES): raise IntegrityError("Unsupported process variables")
        for variable,rule in p["variables"].items():
            if not isinstance(rule,dict) or set(rule)!={"unit","minimum","maximum"} or rule["unit"]!=VARIABLES[variable] or number(rule["minimum"])>number(rule["maximum"]):
                raise IntegrityError("Process limits need supported units and ordered bounds")
    else:
        if set(p)!={"culture_version","source_digest","variable","value_unit","time_unit","clock_origin_utc","alignment","kind_of_observation","basis"}:
            raise IntegrityError("Invalid realized trajectory")
        if db.get(p["culture_version"])["kind"]!="culture": raise IntegrityError("Trajectory needs exact culture version")
        if p["variable"] not in VARIABLES or p["value_unit"]!=VARIABLES[p["variable"]] or p["time_unit"] not in TIME_FACTORS: raise IntegrityError("Unsupported trajectory units")
        utc(p["clock_origin_utc"])
        if p["alignment"] not in {"culture_start","unresolved"} or p["kind_of_observation"]!="realized": raise IntegrityError("A nominal setpoint is not a realized trajectory")
        if p["source_digest"] not in artifacts: raise IntegrityError("Retain realized sensor bytes")
        points(db,p)


def evaluate(db,culture_version,trajectory_versions,policy_version):
    culture=db.get(culture_version);policy=db.get(policy_version)
    if culture["kind"]!="culture" or policy["kind"]!="process_policy": raise IntegrityError("Expected culture and process policy")
    if not isinstance(trajectory_versions,list) or any(not isinstance(v,str) for v in trajectory_versions) or len(set(trajectory_versions))!=len(trajectory_versions): raise IntegrityError("Unique trajectory versions required")
    verify_closure(db,policy_version);p=policy["payload"];start=number(p["start_h"]);end=number(p["end_h"])
    issues=[];rows=[];covered=set();origins=set();used={policy_version};conflict=False
    for version in trajectory_versions:
        r=db.get(version)
        if r["kind"]!="trajectory": raise IntegrityError("Expected realized trajectory")
        verify_closure(db,version);q=r["payload"];used.add(version)
        validate_process(db,"trajectory",q,r["dependencies"],r["artifacts"])
        if q["variable"] not in p["variables"]: continue
        if q["culture_version"]!=culture_version or q["alignment"]!="culture_start" or outdated_sources(db,version):
            issues.append({"version":version,"reason":"wrong_culture_unresolved_clock_or_superseded_source"});continue
        origins.add(utc(q["clock_origin_utc"]).isoformat())
        observed=[(t,v) for t,v in points(db,q) if start<=t<=end]
        if len(observed)<2 or observed[0][0]!=start or observed[-1][0]!=end:
            issues.append({"version":version,"reason":"window_not_observed_at_both_endpoints"});continue
        gap=max(b[0]-a[0] for a,b in zip(observed,observed[1:]));low=min(v for _,v in observed);high=max(v for _,v in observed)
        rule=p["variables"][q["variable"]]
        if gap>number(p["max_gap_h"]):issues.append({"version":version,"reason":"sampling_gap_exceeds_policy"})
        if low<number(rule["minimum"]) or high>number(rule["maximum"]):
            conflict=True;issues.append({"version":version,"reason":"observed_limits_exceeded"})
        review=assessment_summary(db,version)["dimensions"]["comparability"]
        used.update(review["assessment_versions"])
        if review["status"]!="supported":issues.append({"version":version,"reason":"clock_and_sensor_comparability_unassessed"})
        covered.add(q["variable"])
        rows.append({"version":version,"variable":q["variable"],"minimum":decimal_text(low),"maximum":decimal_text(high),"max_gap_h":decimal_text(gap),"observations":len(observed)})
    if len(origins)>1:issues.append({"reason":"conflicting_culture_clock_origins"})
    missing=sorted(set(p["variables"])-covered)
    return {"status":"conflict" if conflict else "open" if missing or issues else "within_declared_limits",
            "missing_variables":missing,"trajectories":rows,"issues":issues,"evidence_versions":sorted(used),
            "meaning":"Observed points and declared bounds only; no interpolation, unobserved-interval guarantee, process equivalence or scale-up prediction."}
