"""Conditional first-order uncertainty for one linear peak-area assay model."""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction

from .core import IntegrityError
from .domain import number
from .contracts import read_json
from .calc import FACTORS, decimal_text
from .graph import verify_closure

VARIABLES = ("response", "intercept", "slope", "dilution")


def rational(value): return Fraction(number(value))


def render(value):
    with localcontext() as ctx:
        ctx.prec=50;ctx.rounding=ROUND_HALF_EVEN
        return decimal_text(Decimal(value.numerator)/Decimal(value.denominator))


def covariance_matrix(values, n):
    if not isinstance(values,list) or len(values)!=n or any(not isinstance(r,list) or len(r)!=n for r in values):
        raise IntegrityError("Explicit square covariance matrix required")
    matrix=[[rational(v) for v in row] for row in values]
    if any(matrix[i][j]!=matrix[j][i] for i in range(n) for j in range(n)): raise IntegrityError("Covariance must be symmetric")
    work=[row[:] for row in matrix]
    for i in range(n):
        pivot=work[i][i]
        if pivot<0 or pivot==0 and any(work[i][j]!=0 for j in range(i+1,n)):
            raise IntegrityError("Covariance must be positive semidefinite")
        if pivot:
            for j in range(i+1,n):
                for k in range(i+1,n):work[j][k]-=work[j][i]*work[i][k]/pivot
    return matrix


def model(values, scale="1"):
    if not isinstance(values,dict) or set(values)!=set(VARIABLES): raise IntegrityError("Declare all four linear-model variables")
    r,b,a,d=[rational(values[k]) for k in VARIABLES];f=rational(scale)
    if a<=0 or d<=0 or f<=0: raise IntegrityError("Positive slope, dilution and unit scale required")
    value=(r-b)*d/a*f
    if value<0: raise IntegrityError("Negative model concentration")
    return value,[d/a*f,-d/a*f,-(r-b)*d/a**2*f,(r-b)/a*f]


def quadratic(g,c):return sum(g[i]*c[i][j]*g[j] for i in range(len(g)) for j in range(len(g)))


def propagate(values,covariance,*,scale="1"):
    value,g=model(values,scale);c=covariance_matrix(covariance,4)
    return {"value":render(value),"variance":render(quadratic(g,c)),"sensitivity":[render(v) for v in g],
            "model":"linear-first-order:1","coverage":"Conditional on the supplied covariance; unmodelled uncertainty is not zero."}


def contrast(values_a,values_b,joint_covariance,*,scale_a="1",scale_b="1"):
    a,ga=model(values_a,scale_a);b,gb=model(values_b,scale_b);c=covariance_matrix(joint_covariance,8)
    return {"difference":render(a-b),"variance":render(quadratic(ga+[-v for v in gb],c)),
            "model":"linear-first-order-contrast:1","meaning":"Joint covariance is explicitly supplied, never inferred from similar calibration labels."}


def assay_dependencies(kind,p):
    refs=[("calibration_version","calibration")] if kind=="assay_profile" else [("measurement_version","measurement"),("assay_profile_version","assay")]
    return [{"role":role,"version_id":p[field]} for field,role in refs if field in p]


def validate_assay(db,kind,p,deps,artifacts):
    if deps!=sorted(assay_dependencies(kind,p),key=lambda d:(d["role"],d["version_id"])): raise IntegrityError("Assay dependencies disagree")
    if kind=="assay_profile":
        if set(p)!={"calibration_version","matrix","readout","measurand_id","validation_scope","source_digest","basis"}: raise IntegrityError("Invalid scoped assay profile")
        calibration=db.get(p["calibration_version"])
        if calibration["kind"]!="calibration" or p["readout"] not in {"direct_concentration","proxy"}: raise IntegrityError("Unsupported assay/readout")
        for field in ("matrix","measurand_id","validation_scope","basis"):
            if not isinstance(p[field],str) or not p[field].strip(): raise IntegrityError("Assay scope cannot be empty")
        if p["measurand_id"]!=calibration["payload"]["analyte_id"]: raise IntegrityError("Assay measurand differs from calibration")
        if p["source_digest"] not in artifacts: raise IntegrityError("Retain assay observation bytes")
        raw=read_json(db,p["source_digest"])
        if set(raw)!={"schema","calibration_version","matrix","observations"} or raw["schema"]!="assay-validation-observations/1" or raw["calibration_version"]!=p["calibration_version"] or raw["matrix"]!=p["matrix"]:
            raise IntegrityError("Assay source bindings disagree")
        rows=raw["observations"]
        if not isinstance(rows,list) or not 1<=len(rows)<=1000: raise IntegrityError("Bounded validation observations required")
        expected=calibration["payload"]["concentration_unit"] if p["readout"]=="direct_concentration" else "area"
        for row in rows:
            if not isinstance(row,dict) or set(row)!={"nominal","observed","unit"} or row["unit"]!=expected or min(number(row["nominal"]),number(row["observed"]))<0:
                raise IntegrityError("Invalid assay observation")
    else:
        if set(p)!={"measurement_version","assay_profile_version","source_digest","result"}: raise IntegrityError("Invalid uncertainty result")
        if p["source_digest"] not in artifacts: raise IntegrityError("Retain uncertainty model bytes")
        if p["result"]!=compute(db,p["measurement_version"],p["assay_profile_version"],p["source_digest"]): raise IntegrityError("Uncertainty result differs from declared model")


def compute(db,measurement_version,assay_profile_version,source_digest):
    m=db.get(measurement_version);profile=db.get(assay_profile_version)
    if m["kind"]!="measurement" or profile["kind"]!="assay_profile": raise IntegrityError("Expected measurement and scoped assay profile")
    for v in (measurement_version,assay_profile_version):verify_closure(db,v)
    p=m["payload"];a=profile["payload"];c=db.get(p["calibration_version"])["payload"]
    validate_assay(db,"assay_profile",a,profile["dependencies"],profile["artifacts"])
    sample=db.get(p["sample_version"])["payload"]
    if a["calibration_version"]!=p["calibration_version"] or a["matrix"]!=sample.get("compartment"):
        raise IntegrityError("Assay matrix or calibration does not cover measurement")
    source=read_json(db,source_digest)
    if set(source)!={"schema","measurement_version","covariance","basis"} or source["schema"]!="linear-uncertainty/1" or source["measurement_version"]!=measurement_version or not isinstance(source["basis"],str) or not source["basis"].strip():
        raise IntegrityError("Source-bound uncertainty model and basis required")
    covariance_matrix(source["covariance"],4)
    if a["readout"]=="proxy":return {"status":"proxy_only","value":None,"variance":None,"unit":"g/L","meaning":"Proxy is not established product concentration."}
    if p["quantification"]!="quantified":return {"status":"censored_or_unreviewed","value":None,"variance":None,"unit":"g/L","meaning":"Censoring is preserved; no zero imputation."}
    if p["qc"]!="pass" or not number(c["min_response"])<=number(p["response"])<=number(c["max_response"]):
        return {"status":"outside_supported_assay_scope","value":None,"variance":None,"unit":"g/L"}
    values={"response":p["response"],"intercept":c["intercept"],"slope":c["slope"],"dilution":p["dilution"]}
    result=propagate(values,source["covariance"],scale=str(FACTORS[c["concentration_unit"]]))
    return {"status":"computed_conditionally","unit":"g/L",**result}


def freeze_uncertainty(db,entity_id,measurement_version,assay_profile_version,source,**kwargs):
    with db.atomic():
        key=db.objects.add(source)
        result=compute(db,measurement_version,assay_profile_version,key)
        return db.capture(entity_id,"uncertainty_result",{"measurement_version":measurement_version,
            "assay_profile_version":assay_profile_version,"source_digest":key,"result":result},artifacts=[key],**kwargs)
