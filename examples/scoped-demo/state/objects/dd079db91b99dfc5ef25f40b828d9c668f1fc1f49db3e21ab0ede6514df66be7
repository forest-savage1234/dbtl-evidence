"""Frozen scoped decision packets; a research workflow, not scientific certification."""
from collections import defaultdict
from decimal import localcontext, ROUND_HALF_EVEN
from html import escape
import json
from pathlib import Path

from .core import IntegrityError, digest
from .domain import number
from .pools import journal, compute_snapshot, replay_snapshot
from .graph import verify_closure, outdated_sources
from .datasets import source_manifest
from .calc import evaluate as base_evaluate, decimal_text
from .assessments import summary as assessment_summary
from .units import summarize as unit_summary, ancestry
from .genotypes import evaluate as genotype_evaluate, utc
from .process import evaluate as process_evaluate
from .uncertainty import compute as uncertainty_compute


class HistoricalView:
    """Read only application view. Closure SQL is safe: dependencies always point earlier."""
    def __init__(self, db, watermark=None):
        self.watermark,self.records,self.heads,self.journal_sha256=journal(db,watermark)
        self.conn=db.conn;self.objects=db.objects

    def get(self,version):
        if version not in self.records:raise IntegrityError("Version is outside the frozen registry history")
        return self.records[version]

    def latest(self,entity):
        if entity not in self.heads:raise IntegrityError("Entity is outside the frozen registry history")
        return self.heads[entity]

    def versions(self,kind=None,heads_only=False):
        values=self.heads.values() if heads_only else self.records.values()
        return sorted((r for r in values if kind is None or r["kind"]==kind),key=lambda r:(r["entity_id"],r["revision"]))


def packet_dependencies(kind,p):
    refs={"packet_policy":[("base_policy_version","base_policy"),("process_policy_version","process_policy")],
          "packet":[("cohort_version","cohort"),("policy_version","packet_policy"),("pool_snapshot_version","pool_snapshot")],
          "advance":[("packet_version","packet")]}
    result=[{"role":role,"version_id":p[field]} for field,role in refs[kind] if field in p]
    if kind=="packet":
        result += [{"role":"evidence","version_id":v} for v in p.get("result",{}).get("evidence_versions",[])]
        result += [{"role":"literature_reference","version_id":v} for v in p.get("reference_versions",[])]
    if kind=="advance":result += [{"role":"selected_strain","version_id":v} for v in p.get("selected_strain_versions",[])]
    return result


def validate_policy(db,p):
    if set(p)!={"base_policy_version","process_policy_version","minimum_culture_units","genotype","intended_use","target_domain","basis"}:
        raise IntegrityError("Packet policy requires explicit assay, genotype, process and use boundaries")
    if db.get(p["base_policy_version"])["kind"]!="policy" or db.get(p["process_policy_version"])["kind"]!="process_policy": raise IntegrityError("Wrong comparison or process policy")
    if type(p["minimum_culture_units"]) is not int or p["minimum_culture_units"]<2:raise IntegrityError("At least two assessed culture units per strain are required by this profile")
    for field in ("intended_use","target_domain","basis"):
        if not isinstance(p[field],str) or not p[field].strip():raise IntegrityError("Packet use and criteria need a basis")
    g=p["genotype"]
    if not isinstance(g,dict) or set(g)!={"required_regions","as_of","max_age_h","minimum_generation","required_scope"}:raise IntegrityError("Complete genotype scope required")
    utc(g["as_of"])
    if not isinstance(g["required_regions"],list) or not g["required_regions"] or any(not isinstance(v,str) or not v.strip() for v in g["required_regions"]) or len(set(g["required_regions"]))!=len(g["required_regions"]):raise IntegrityError("Explicit genotype regions required")
    if number(g["max_age_h"])<0 or type(g["minimum_generation"]) is not int or g["minimum_generation"]<0 or g["required_scope"] not in {"clone","population"}:raise IntegrityError("Invalid genotype eligibility window")


def compute(view,cohort_version,policy_version,pool_snapshot_version,reference_versions):
    cohort=view.get(cohort_version);policy=view.get(policy_version);anchor=view.get(pool_snapshot_version)
    if cohort["kind"]!="cohort" or policy["kind"]!="packet_policy" or anchor["kind"]!="pool_snapshot":raise IntegrityError("Packet requires cohort, packet policy and bounded pool snapshot")
    validate_policy(view,policy["payload"]);p=policy["payload"];issues=[];used={cohort_version,policy_version,pool_snapshot_version}
    for v in sorted(used):verify_closure(view,v)
    replay_snapshot(view,pool_snapshot_version)
    scope=anchor["payload"];pool=view.latest(view.get(scope["pool_version"])["entity_id"])
    current=compute_snapshot(view,pool["id"],view.watermark)
    if any(current.get(k)!=scope.get(k) for k in ("pool_version","candidates","availability_versions")):
        issues.append({"scope":"pool","reason":"membership_eligibility_or_scope_changed_since_snapshot"})
    candidates={r["measurement_version"] for r in current["candidates"]};included={r["measurement_version"] for r in current["candidates"] if r["status"]=="included"}
    used.update(candidates);used.update(current.get("availability_versions",[]));used.add(pool["id"])
    members=set(cohort["payload"]["measurement_versions"])
    for v in sorted(candidates-members):verify_closure(view,v)
    if not included<=members or not members<=candidates:issues.append({"scope":"pool","reason":"cohort_does_not_cover_registered_eligible_candidates"})
    if any(r["status"]=="uncertain" for r in current["candidates"]):issues.append({"scope":"pool","reason":"candidate_eligibility_unresolved"})
    for v in (cohort_version,policy_version):
        if outdated_sources(view,v):issues.append({"scope":"inputs","reason":"superseded_evidence","version":v})
    base=base_evaluate(view,cohort_version,p["base_policy_version"],historical=True)
    pool_rows={r["measurement_version"]:r for r in current["candidates"]}
    for row in base["included"]:
        if row["measurement_version"] not in included:
            pool_row=pool_rows.get(row["measurement_version"],{"status":"outside_pool","reasons":[]})
            base["excluded"].append({"measurement_version":row["measurement_version"],"reasons":["pool:"+pool_row["status"],*pool_row["reasons"]]})
    base["included"]=[r for r in base["included"] if r["measurement_version"] in included]
    if not base["included"]:issues.append({"scope":"cohort","reason":"no_eligible_quantified_measurements"})
    ms=[r["measurement_version"] for r in base["included"]];all_units=unit_summary(view,ms,minimum=p["minimum_culture_units"])
    used.update(all_units["evidence_versions"])
    if all_units["issues"]:issues.append({"scope":"physical_units","reason":"unit_identity_or_independence_unresolved","details":all_units["issues"]})
    by_strain=defaultdict(list);checks=[];process_checks={}
    observations=view.versions("genotype_observation",heads_only=True);uncertainties=view.versions("uncertainty_result",heads_only=True);trajectories=view.versions("trajectory",heads_only=True)
    for row in base["included"]:
        v=row["measurement_version"];by_strain[row["strain_version"]].append(v);a=assessment_summary(view,v);used.add(v)
        for dimension in ("measurement","sample_identity","comparability"):
            used.update(a["dimensions"][dimension]["assessment_versions"])
            if a["dimensions"][dimension]["status"]!="supported":issues.append({"scope":"measurement","version":v,"reason":"unresolved_"+dimension})
        materials=ancestry(view,v)[1:];culture=materials[-1]
        gs=[r["id"] for r in observations if r["payload"]["material_version"] in materials]
        genotype=genotype_evaluate(view,v,gs,**p["genotype"]);used.update(genotype["evidence_versions"])
        if genotype["status"]!="supported_for_declared_regions":issues.append({"scope":"genotype","version":v,"reason":genotype["status"]})
        urs=[r for r in uncertainties if r["payload"]["measurement_version"]==v];assays=[]
        if not urs:issues.append({"scope":"assay","version":v,"reason":"missing_conditional_uncertainty_and_assay_profile"})
        for ur in urs:
            verify_closure(view,ur["id"]);up=ur["payload"];used.add(ur["id"]);used.add(up["assay_profile_version"])
            result=uncertainty_compute(view,v,up["assay_profile_version"],up["source_digest"])
            if result!=up["result"]:raise IntegrityError("Frozen uncertainty does not reconstruct")
            ar=assessment_summary(view,up["assay_profile_version"])["dimensions"]["measurement"];used.update(ar["assessment_versions"])
            if result["status"]!="computed_conditionally" or ar["status"]!="supported" or outdated_sources(view,ur["id"]):
                issues.append({"scope":"assay","version":ur["id"],"reason":"assay_validity_or_uncertainty_scope_unresolved"})
            assays.append({"version":ur["id"],"result":result,"assay_assessment":ar["status"]})
        if culture not in process_checks:
            ts=[r["id"] for r in trajectories if r["payload"]["culture_version"]==culture]
            proc=process_evaluate(view,culture,ts,p["process_policy_version"]);used.update(proc["evidence_versions"]);process_checks[culture]=proc
            if proc["status"]!="within_declared_limits":issues.append({"scope":"process","version":culture,"reason":proc["status"]})
        checks.append({"measurement_version":v,"assessments":a,"genotype":genotype,"assays":assays})
    summaries=[];values={r["measurement_version"]:number(r["titer_g_l"]) for r in base["included"]}
    with localcontext() as ctx:
        ctx.prec=50;ctx.rounding=ROUND_HALF_EVEN
        for strain,versions in sorted(by_strain.items()):
            units=unit_summary(view,versions,minimum=p["minimum_culture_units"]);means=[sum(values[v] for v in r["measurement_versions"])/len(r["measurement_versions"]) for r in units["units"]]
            eligible=units["eligible_for_scoped_descriptive_comparison"]
            if not eligible:issues.append({"scope":"replication","version":strain,"reason":"insufficient_assessed_independent_culture_units"})
            summaries.append({"strain_version":strain,"strain_id":view.get(strain)["entity_id"],"units":units,
                              "mean_g_l":decimal_text(sum(means)/len(means)) if means else None,"eligible":eligible})
    refs=[]
    if not isinstance(reference_versions,list) or any(not isinstance(v,str) for v in reference_versions) or len(set(reference_versions))!=len(reference_versions):raise IntegrityError("Unique literature references required")
    for v in reference_versions:
        r=view.get(v)
        if r["kind"]!="literature_evidence":raise IntegrityError("Only separate literature receipts can be reference inputs")
        verify_closure(view,v)
        from .handoff import validate_handoff
        validate_handoff(view,r["payload"],r["dependencies"],r["artifacts"])
        refs.append({"version":v,"origin":r["payload"]["origin"],"consumer_dimensions":r["payload"]["consumer_dimensions"],"role":"reference_only; excluded from local replication and titer means"})
        if r["payload"]["use_scope"]["target_domain"]!=p["target_domain"]:issues.append({"scope":"literature","version":v,"reason":"declared_target_domain_mismatch"})
        if outdated_sources(view,v):issues.append({"scope":"literature","version":v,"reason":"superseded_reference"})
    if not issues:
        for row in summaries:row["descriptive_rank"]=1+sum(number(o["mean_g_l"])>number(row["mean_g_l"]) for o in summaries)
    return {"algorithm_id":"scoped-decision-packet:1","state":"withheld" if issues else "ready_for_scoped_human_review",
            "issues":issues,"pool_coverage":current["coverage"],"excluded":base["excluded"],"summaries":summaries,
            "measurement_checks":checks,"process_checks":process_checks,"literature_references":refs,"evidence_versions":sorted(used),
            "interpretation":"Conditional descriptive comparison under declared criteria and asserted reviews. No automatic advancement, scientific certification, significance, causal inference or industrial-transfer claim."}


def validate_packet(db,kind,p,deps,artifacts):
    if deps!=sorted(packet_dependencies(kind,p),key=lambda d:(d["role"],d["version_id"])):raise IntegrityError("Packet dependencies disagree")
    if kind=="packet_policy":validate_policy(db,p);return
    if kind=="advance":
        if set(p)!={"packet_version","selected_strain_versions","rationale"} or not isinstance(p["rationale"],str) or not p["rationale"].strip():raise IntegrityError("Explicit reviewed selection and rationale required")
        state=status(db,p["packet_version"]);packet=db.get(p["packet_version"])["payload"]
        if state["requires_reassessment"] or packet["result"]["state"]!="ready_for_scoped_human_review":raise IntegrityError("Selection requires a current packet with all scoped gates satisfied")
        choices=p["selected_strain_versions"];eligible={r["strain_version"] for r in packet["result"]["summaries"] if r["eligible"]}
        if not isinstance(choices,list) or not choices or any(not isinstance(v,str) for v in choices) or len(set(choices))!=len(choices) or not set(choices)<=eligible:raise IntegrityError("Selection must name unique eligible packet strains")
        return
    fields={"cohort_version","policy_version","pool_snapshot_version","reference_versions","watermark","journal_sha256","algorithm_manifest","result","result_sha256"}
    if set(p)!=fields or p["algorithm_manifest"]!=source_manifest():raise IntegrityError("Packet source/runtime or shape differs")
    if not set(p["algorithm_manifest"]["files"].values())<=set(artifacts):raise IntegrityError("Retain packet computation sources")
    view=HistoricalView(db)
    if view.watermark!=p["watermark"] or view.journal_sha256!=p["journal_sha256"]:raise IntegrityError("New packet must freeze the current transaction history")
    result=compute(view,p["cohort_version"],p["policy_version"],p["pool_snapshot_version"],p["reference_versions"])
    if p["result"]!=result or p["result_sha256"]!=digest(result):raise IntegrityError("Packet output does not reconstruct")


def freeze(db,entity_id,cohort_version,policy_version,pool_snapshot_version,*,reference_versions=None,**kwargs):
    with db.atomic():
        view=HistoricalView(db);manifest=source_manifest();root=Path(__file__).parent
        artifacts=[db.objects.add(root/name) for name in manifest["files"]]
        references=[] if reference_versions is None else reference_versions
        result=compute(view,cohort_version,policy_version,pool_snapshot_version,references)
        return db.capture(entity_id,"packet",{"cohort_version":cohort_version,"policy_version":policy_version,
            "pool_snapshot_version":pool_snapshot_version,"reference_versions":references,"watermark":view.watermark,
            "journal_sha256":view.journal_sha256,"algorithm_manifest":manifest,"result":result,"result_sha256":digest(result)},artifacts=artifacts,**kwargs)


def replay(db,version):
    r=db.get(version)
    if r["kind"]!="packet":raise IntegrityError("Expected decision packet")
    verify_closure(db,version);p=r["payload"]
    if p["algorithm_manifest"]!=source_manifest():raise IntegrityError("Packet replay blocked: restore recorded source/runtime; archived code is never auto-executed")
    view=HistoricalView(db,p["watermark"])
    if view.journal_sha256!=p["journal_sha256"]:raise IntegrityError("Packet registry history differs")
    computed=compute(view,p["cohort_version"],p["policy_version"],p["pool_snapshot_version"],p["reference_versions"])
    if computed!=p["result"] or digest(computed)!=p["result_sha256"]:raise IntegrityError("Packet replay differs")
    return {"ok":True,"packet_version":version,"historical_state":computed["state"],"result_sha256":digest(computed),
            "meaning":"Historical software reconstruction only; does not establish current eligibility or scientific truth."}


def status(db,version):
    with db.atomic():
        replay(db,version);r=db.get(version);p=r["payload"]
        try:
            result=compute(HistoricalView(db),p["cohort_version"],p["policy_version"],p["pool_snapshot_version"],p["reference_versions"])
            current_digest=digest(result);issues=result["issues"]
        except IntegrityError as exc:current_digest=digest({"blocked":str(exc)});issues=[{"reason":str(exc)}]
        superseded=db.latest(r["entity_id"])["id"]!=version
        changed=current_digest!=p["result_sha256"] or bool(outdated_sources(db,version)) or superseded
        return {"packet_version":version,"state":"reassessment_pending" if changed else p["result"]["state"],
                "requires_reassessment":changed,"current_result_sha256":current_digest,"issues":issues,
                "fingerprint":digest({"packet":version,"current":current_digest,"superseded":superseded})}


def render(db,version):
    replayed=replay(db,version);r=db.get(version);current=status(db,version)
    body=escape(json.dumps({"record":r,"policy":db.get(r["payload"]["policy_version"]),"historical_replay":replayed,"current_status":current},indent=2))
    result=r["payload"]["result"]
    comparisons="".join("<tr>"+"".join("<td>"+escape(str(v))+"</td>" for v in [s["strain_id"],s["mean_g_l"] or "Unavailable",s["units"]["declared_culture_unit_n"],s["units"]["assessed_culture_unit_n"],s.get("descriptive_rank","Withheld")])+"</tr>" for s in result["summaries"])
    issues="".join("<li>"+escape(i.get("scope","evidence")+": "+i["reason"].replace("_"," "))+"</li>" for i in current["issues"])
    if not issues:issues="<li>No unresolved requirement detected under the recorded profile. Scientific judgments remain asserted.</li>"
    checks="".join("<tr>"+"".join("<td>"+escape(str(v))+"</td>" for v in [s["measurement_version"],s["assessments"]["dimensions"]["measurement"]["status"],s["assessments"]["dimensions"]["sample_identity"]["status"],s["genotype"]["status"],", ".join(a["result"]["status"] for a in s["assays"]) or "Missing"])+"</tr>" for s in result["measurement_checks"])
    return "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'none'\"><title>DBTL scoped decision packet</title><style>body{font:16px system-ui;max-width:1080px;margin:3rem auto;padding:1rem;color:#17343b;line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f5;padding:1.2rem}h1{font-size:2.4rem;line-height:1.15}table{border-collapse:collapse;width:100%;font-size:.85rem}th,td{text-align:left;padding:.7rem;border-bottom:1px solid #d6e1e0;overflow-wrap:anywhere}th{background:#edf3f1}.scroll{overflow-x:auto}.state{padding:1rem;border-left:5px solid #a76414;background:#fff3dc}h2{margin-top:2.5rem}details{margin-top:2rem}</style><p>DBTL EVIDENCE · RESEARCH WORKFLOW</p><h1>Scoped decision packet</h1><div class='state'><b>Current registered-evidence state: "+escape(current["state"])+"</b><br>Recorded state: "+escape(result["state"])+"</div><p>These are conditional descriptive results under declared criteria and reviewer assertions. This record does not certify scientific validity or authorize an experiment. Historical replay succeeds only for the recorded source/runtime.</p><h2>Recorded comparisons</h2><p>Ranks below belong to the frozen record. Check current issues before any reuse. Units are g/L; physical roots receive equal weight after technical aggregation.</p><div class='scroll'><table><tr><th>Strain</th><th>Mean g/L</th><th>Declared cultures</th><th>Assessed cultures</th><th>Recorded rank</th></tr>"+comparisons+"</table></div><h2>Current review requirements</h2><ul>"+issues+"</ul><h2>Recorded evidence scope</h2><div class='scroll'><table><tr><th>Measurement</th><th>Measurement review</th><th>Sample identity</th><th>Genotype scope</th><th>Assay computation</th></tr>"+checks+"</table></div><p>Pool coverage: "+escape(result["pool_coverage"])+". Genotype review horizon is fixed by policy. First-order uncertainty omits unidentified effects; ranks do not establish significance or industrial transfer.</p><details><summary>Exact retained record, exclusions, process checks, source hashes and replay</summary><pre>"+body+"</pre></details></html>"
