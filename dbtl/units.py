"""Declared physical units and assessed independence, separate from entity labels."""
from .core import IntegrityError, digest, identifier
from .graph import verify_closure, outdated_sources
from .assessments import summary as assessment_summary


def unit_dependencies(kind,p):
    if kind=="experimental_unit":
        return [{"role":"parent_unit","version_id":p["parent_version"]}] if p.get("parent_version") else []
    return [{"role":role,"version_id":p[field]} for field,role in [("subject_version","subject"),("unit_version","unit")] if field in p]


def assignment_id(db,subject_version):
    return "unit-link:"+digest(db.get(subject_version)["entity_id"])


def validate_unit_record(db,kind,p,deps,entity_id):
    if deps!=sorted(unit_dependencies(kind,p),key=lambda d:(d["role"],d["version_id"])): raise IntegrityError("Unit dependencies disagree")
    if not isinstance(p.get("basis"),str) or not p["basis"].strip(): raise IntegrityError("Unit mapping needs a declared basis")
    if kind=="experimental_unit":
        if set(p)!={"physical_id","role","parent_version","basis"} or p["role"] not in {"culture","aliquot","acquisition"}: raise IntegrityError("Invalid experimental unit")
        identifier(p["physical_id"])
        for r in db.versions("experimental_unit",heads_only=True):
            if r["entity_id"]!=entity_id and r["payload"]["physical_id"]==p["physical_id"]: raise IntegrityError("Physical unit already has a canonical entity")
        if p["role"]=="culture":
            if p["parent_version"] is not None: raise IntegrityError("Culture is the root experimental unit in this bounded profile")
        else:
            parent=db.get(p["parent_version"])
            allowed={"culture"} if p["role"]=="aliquot" else {"culture","aliquot"}
            if parent["kind"]!="experimental_unit" or parent["payload"]["role"] not in allowed: raise IntegrityError("Unsupported unit hierarchy")
    else:
        if set(p)!={"subject_version","unit_version","basis"} or entity_id!=assignment_id(db,p["subject_version"]): raise IntegrityError("Use one versioned canonical unit link per subject entity")
        if db.get(p["subject_version"])["kind"] not in {"culture","sample","measurement","quantity"} or db.get(p["unit_version"])["kind"]!="experimental_unit": raise IntegrityError("Invalid subject or physical unit")


def assign(db,subject_version,unit_version,*,basis,**kwargs):
    return db.capture(assignment_id(db,subject_version),"unit_assignment",{"subject_version":subject_version,"unit_version":unit_version,"basis":basis},**kwargs)


def root_unit(db,version):
    r=db.get(version)
    for _ in range(3):
        if r["kind"]!="experimental_unit": raise IntegrityError("Expected physical unit")
        if r["payload"]["role"]=="culture": return r
        r=db.get(r["payload"]["parent_version"])
    raise IntegrityError("Unsupported or cyclic unit hierarchy")


def ancestry(db,version):
    result=[];r=db.get(version)
    for _ in range(5):
        result.append(r["id"]);p=r["payload"]
        field={"quantity":"subject_version","measurement":"sample_version","sample":"culture_version"}.get(r["kind"])
        if field is None: return result
        r=db.get(p[field])
    raise IntegrityError("Unsupported material ancestry")


def summarize(db,measurement_versions,*,minimum=2,assignment_versions=None):
    if type(minimum) is not int or minimum<1: raise IntegrityError("Positive minimum unit count required")
    if not isinstance(measurement_versions,list) or any(not isinstance(v,str) for v in measurement_versions) or len(set(measurement_versions))!=len(measurement_versions): raise IntegrityError("Unique measurement versions required for unit analysis")
    bindings=[db.get(v) for v in assignment_versions] if assignment_versions is not None else db.versions("unit_assignment",heads_only=True)
    if any(r["kind"]!="unit_assignment" for r in bindings): raise IntegrityError("Expected unit assignments")
    by_subject={}
    for r in bindings:by_subject.setdefault(r["payload"]["subject_version"],[]).append(r)
    groups={};issues=[];used=set();acquisitions={}
    for v in measurement_versions:
        record=db.get(v)
        if record["kind"]!="measurement": raise IntegrityError("Unit analysis expects measurement versions")
        links=[link for subject in ancestry(db,v) for link in by_subject.get(subject,[])]
        roots={}
        if not links:issues.append({"measurement_version":v,"reason":"missing_unit_mapping"});continue
        for link in links:
            verify_closure(db,link["id"]);used.add(link["id"])
            if outdated_sources(db,link["id"]):issues.append({"measurement_version":v,"reason":"superseded_unit_mapping"})
            unit=db.get(link["payload"]["unit_version"]);root=root_unit(db,unit["id"]);roots[root["id"]]=root;used.add(root["id"])
            if unit["payload"]["role"]=="acquisition":acquisitions.setdefault(unit["id"],set()).add(v)
        if len(roots)!=1:issues.append({"measurement_version":v,"reason":"conflicting_unit_mapping"});continue
        root=next(iter(roots.values()));groups.setdefault(root["id"],[]).append(v)
    for acquisition,values in acquisitions.items():
        if len(values)>1:issues.append({"reason":"duplicate_physical_acquisition","unit_version":acquisition,"measurement_versions":sorted(values)})
    assessed=0;rows=[]
    for root,values in sorted(groups.items()):
        strains={db.get(ancestry(db,v)[-1])["payload"]["strain_version"] for v in values}
        if len(strains)>1:issues.append({"unit_version":root,"reason":"one_physical_culture_mapped_to_multiple_strain_versions"})
        review=assessment_summary(db,root)["dimensions"]["replicate_independence"]
        used.update(review["assessment_versions"])
        if review["status"]=="supported":assessed+=1
        else:issues.append({"unit_version":root,"reason":"independence_not_assessed_supported"})
        rows.append({"unit_version":root,"measurement_versions":sorted(values),"independence_assessment":review["status"]})
    return {"declared_culture_unit_n":len(groups),"assessed_culture_unit_n":assessed,"minimum":minimum,
            "eligible_for_scoped_descriptive_comparison":not issues and assessed>=minimum,
            "units":rows,"issues":issues,"evidence_versions":sorted(used),
            "meaning":"Counts follow declared physical mappings and scoped reviewer assessments; physical identity is not authenticated."}
