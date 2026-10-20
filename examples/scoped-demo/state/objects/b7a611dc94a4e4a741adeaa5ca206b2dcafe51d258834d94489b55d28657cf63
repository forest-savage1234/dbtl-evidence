"""Source-bound quantity semantics and explicitly chosen ratio estimators."""
import csv
import io
from decimal import Decimal, localcontext, ROUND_HALF_EVEN

from .core import IntegrityError, identifier
from .domain import number
from .graph import verify_closure, outdated_sources
from .calc import decimal_text

UNITS = {"g":("mass","1"),"mg":("mass","0.001"),"kg":("mass","1000"),
         "g/L":("concentration","1"),"mg/L":("concentration","0.001"),"ug/L":("concentration","0.000001"),
         "L":("volume","1"),"mL":("volume","0.001"),"h":("time","1"),"min":("time",None),
         "1":("signal","1"),"area":("signal","1")}
BASES = {"product_mass":"mass","substrate_consumed_mass":"mass","substrate_charged_mass":"mass",
         "biomass_mass":"mass","product_concentration":"concentration","culture_volume":"volume",
         "elapsed_time":"time","proxy_response":"signal"}
METRICS = {"mass_yield":("product_mass","substrate_consumed_mass","g/g"),
           "mass_ratio":("product_mass","biomass_mass","g/g"),
           "mass_concentration":("product_mass","culture_volume","g/L"),
           "endpoint_average_productivity":("product_concentration","elapsed_time","g/L/h")}


def quantity_dependencies(kind, payload):
    if kind == "quantity":
        return [{"role":"subject","version_id":payload["subject_version"]}] if "subject_version" in payload else []
    return [{"role":role,"version_id":v} for field,role in [("numerator_versions","numerator"),("denominator_versions","denominator")]
            for v in payload.get(field,[])]


def validate_quantity_record(db, kind, p, deps, artifacts):
    if deps != sorted(quantity_dependencies(kind,p),key=lambda d:(d["role"],d["version_id"])):
        raise IntegrityError("Quantity dependencies differ from declared inputs")
    if kind == "quantity":
        required={"subject_version","source_digest","row","value_column","unit_column","pair_column",
                  "value","unit","pair_id","basis","measurand_id","origin"}
        if set(p)!=required: raise IntegrityError("Quantity needs exact source bindings and semantic basis")
        identifier(p["pair_id"]);identifier(p["measurand_id"])
        if p["origin"] not in {"local","literature","simulation","synthetic"}: raise IntegrityError("Unknown quantity origin")
        subject=db.get(p["subject_version"])
        if p["origin"]=="local" and subject["kind"] not in {"culture","sample","measurement"}:
            raise IntegrityError("Local quantity needs a local material/measurement subject")
        if p["basis"] not in BASES or p["unit"] not in UNITS or BASES[p["basis"]]!=UNITS[p["unit"]][0]:
            raise IntegrityError("Quantity basis and unit dimensions disagree")
        if number(p["value"])<0 and p["basis"]!="proxy_response": raise IntegrityError("Physical quantity must be nonnegative")
        if p["source_digest"] not in artifacts: raise IntegrityError("Retain the source CSV bytes")
        path=db.objects.verify(p["source_digest"])
        if path.stat().st_size>16*1024*1024: raise IntegrityError("Quantity CSV exceeds 16 MiB")
        try:
            reader=csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig")),strict=True)
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames): raise IntegrityError("Duplicate or missing CSV headers")
            if type(p["row"]) is not int or not 2<=p["row"]<=100000: raise IntegrityError("CSV row is a 1-based logical record index, header=1")
            row=next((row for i,row in enumerate(reader,2) if i==p["row"]),None)
            if row is None or any(row.get(p[c])!=p[v] for c,v in [("value_column","value"),("unit_column","unit"),("pair_column","pair_id")]):
                raise IntegrityError("Quantity value, unit or pair ID differs from source row")
        except (UnicodeError,csv.Error,KeyError,TypeError) as exc: raise IntegrityError("Malformed quantity source") from exc
    else:
        if p != compute_result(db,p.get("numerator_versions"),p.get("denominator_versions"),p.get("metric"),p.get("estimator")):
            raise IntegrityError("Quantity result does not reconstruct")


def capture_quantity(db, entity_id, source, *, row, value_column, unit_column, pair_column,
                     subject_version, basis, measurand_id, origin="local", **kwargs):
    source_digest=db.objects.add(source)
    path=db.objects.verify(source_digest)
    if path.stat().st_size>16*1024*1024: raise IntegrityError("Quantity CSV exceeds 16 MiB")
    try:
        rows=list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig")),strict=True))
        raw=rows[row-2] if type(row) is int and row>=2 else None
        if raw is None: raise IntegrityError("Invalid quantity source row")
        payload={"subject_version":subject_version,"source_digest":source_digest,"row":row,
            "value_column":value_column,"unit_column":unit_column,"pair_column":pair_column,
            "value":raw[value_column],"unit":raw[unit_column],"pair_id":raw[pair_column],
            "basis":basis,"measurand_id":measurand_id,"origin":origin}
    except (UnicodeError,csv.Error,KeyError,IndexError,TypeError) as exc: raise IntegrityError("Malformed quantity source binding") from exc
    return db.capture(entity_id,"quantity",payload,artifacts=[source_digest],**kwargs)


def compute_result(db, numerators, denominators, metric, estimator, *, historical=False):
    if metric not in METRICS or estimator not in {"ratio_of_means","mean_of_paired_ratios"}: raise IntegrityError("Explicit supported metric and estimator required")
    expected_n,expected_d,unit=METRICS[metric]
    groups=[]
    with localcontext() as ctx:
        ctx.prec=50;ctx.rounding=ROUND_HALF_EVEN
        for versions,basis in [(numerators,expected_n),(denominators,expected_d)]:
            if not isinstance(versions,list) or not versions or len(versions)>1000 or len(set(versions))!=len(versions):
                raise IntegrityError("Use 1–1000 unique source quantity versions")
            group=[]
            locators=set()
            for v in versions:
                r=db.get(v)
                if r["kind"]!="quantity" or r["payload"]["basis"]!=basis: raise IntegrityError("Denominator/numerator semantic basis does not support metric")
                verify_closure(db,v)
                if not historical and (db.latest(r["entity_id"])["id"]!=v or outdated_sources(db,v)): raise IntegrityError("Superseded quantity evidence requires explicit reconciliation")
                validate_quantity_record(db,"quantity",r["payload"],r["dependencies"],r["artifacts"])
                locator=tuple(r["payload"][k] for k in ["source_digest","row","value_column"])
                if locator in locators: raise IntegrityError("Duplicate source observations are not new replication")
                locators.add(locator)
                p=r["payload"];scale=Decimal(1)/60 if p["unit"]=="min" else Decimal(UNITS[p["unit"]][1])
                group.append((p["pair_id"],number(p["value"])*scale,p["measurand_id"]))
            if len({x[2] for x in group})!=1: raise IntegrityError("Do not pool different measurands")
            groups.append(group)
        ns,ds=groups
        if any(value<=0 for _,value,_ in ds): raise IntegrityError("Denominators must be strictly positive")
        if estimator=="ratio_of_means": value=(sum(x[1] for x in ns)/len(ns))/(sum(x[1] for x in ds)/len(ds))
        else:
            if len({x[0] for x in ns})!=len(ns) or len({x[0] for x in ds})!=len(ds): raise IntegrityError("Duplicate source pair IDs")
            nmap={x[0]:x[1] for x in ns};dmap={x[0]:x[1] for x in ds}
            if set(nmap)!=set(dmap): raise IntegrityError("Missing or unmatched source pairs")
            value=sum(nmap[id]/dmap[id] for id in sorted(nmap))/len(nmap)
        return {"numerator_versions":numerators,"denominator_versions":denominators,"metric":metric,
            "estimator":estimator,"value":decimal_text(value),"unit":unit,"algorithm_id":"typed-ratios:1",
            "interpretation":"Declared source-bound arithmetic only; basis, independence, assay and transfer validity require separate assessment."}


def derive(db, entity_id, numerators, denominators, *, metric, estimator, **kwargs):
    with db.atomic():
        return db.capture(entity_id,"quantity_result",compute_result(db,numerators,denominators,metric,estimator),**kwargs)


def replay_result(db, version):
    r=db.get(version)
    if r["kind"]!="quantity_result": raise IntegrityError("Expected quantity result")
    p=r["payload"]
    expected=compute_result(db,p["numerator_versions"],p["denominator_versions"],p["metric"],p["estimator"],historical=True)
    if expected!=p: raise IntegrityError("Quantity arithmetic does not replay")
    return {"ok":True,"version":version,"value":p["value"],"unit":p["unit"],"scientific_validity":"not_established"}
