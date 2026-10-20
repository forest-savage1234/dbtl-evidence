"""Synthetic, fully scoped packet campaign. Every supporting review is invented."""
import csv
import json
from pathlib import Path

from .core import Instrument, IntegrityError
from .ingest import FIELDS, ingest_csv
from .assessments import DIMENSIONS, assess
from .units import assign
from .pools import snapshot
from .packets import freeze, replay, status, render
from .uncertainty import freeze_uncertainty
from .watches import watch, status as watch_status, acknowledge


def support(db,subject,evidence,dimensions):
    values={d:{"status":"supported" if d in dimensions else "open","basis":"SYNTHETIC fixture review; no real laboratory evidence","evidence_versions":[evidence] if d in dimensions else []} for d in DIMENSIONS}
    return assess(db,"demo2:review:"+db.get(subject)["entity_id"],subject,values,criteria_id="synthetic:packet-design:1")


def source_json(db,path,value):
    path.write_text(json.dumps(value,indent=2)+"\n");return db.objects.add(path)


def add_culture(db,out,name,strain,protocol,extraction,calibration,context,response,*,enrich=True):
    culture=db.capture("demo2:culture:"+name,"culture",{**context,"strain_version":strain["id"],"protocol_version":protocol["id"]})
    sample=db.capture("demo2:sample:"+name,"sample",{"culture_version":culture["id"],"time_h":"24","compartment":"supernatant","extraction_protocol_version":extraction["id"]})
    raw=out/(name+"-signal.csv")
    with raw.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerow({"measurement_id":"demo2:measurement:"+name,
            "sample_version":sample["id"],"calibration_version":calibration["id"],"analyte_id":"demo:product","response":response,
            "response_unit":"area","dilution":"1","qc":"pass","quantification":"quantified","technical_replicate_id":"tech:1","run_id":"demo2:run"})
    m=ingest_csv(db,raw)["measurement_versions"][0]
    parts={"culture":culture,"sample":sample,"strain":strain,"protocol":protocol,"extraction":extraction,"calibration":calibration,"measurement":m}
    if enrich:add_support(db,out,name,parts)
    return parts


def add_support(db,out,name,parts):
    m=parts["measurement"];protocol=parts["protocol"]["id"]
    unit=db.capture("demo2:unit:"+name,"experimental_unit",{"physical_id":"demo2:physical:"+name,"role":"culture","parent_version":None,"basis":"SYNTHETIC independently assigned culture"})
    assign(db,parts["culture"]["id"],unit["id"],basis="SYNTHETIC material mapping")
    support(db,unit["id"],protocol,{"replicate_independence"});support(db,m,protocol,{"measurement","sample_identity","comparability"})
    key=source_json(db,out/(name+"-calls.json"),{"schema":"scoped-genotype-calls/1","calls":[{"region_id":"region:1","expected":"synthetic-intended-state","observed":"synthetic-intended-state","status":"called"}]})
    g=db.capture("demo2:genotype:"+name,"genotype_observation",{"strain_version":parts["strain"]["id"],"material_version":parts["sample"]["id"],
        "observed_at":"2026-10-20T00:00:00Z","generation":10,"scope":"clone","method":"SYNTHETIC precomputed calls","source_digest":key,
        "limitations":"One synthetic region only; no sequencing or stability validation."},artifacts=[key])
    support(db,g["id"],protocol,{"measurement","sample_identity"})
    key=source_json(db,out/(name+"-assay.json"),{"schema":"assay-validation-observations/1","calibration_version":parts["calibration"]["id"],"matrix":"supernatant",
        "observations":[{"nominal":"500","observed":"501","unit":"mg/L"}]})
    assay=db.capture("demo2:assay:"+name,"assay_profile",{"calibration_version":parts["calibration"]["id"],"matrix":"supernatant","readout":"direct_concentration",
        "measurand_id":"demo:product","validation_scope":"SYNTHETIC, not validated","source_digest":key,"basis":"Invented test observation"},artifacts=[key])
    support(db,assay["id"],protocol,{"measurement"})
    cov=[["0" for _ in range(4)] for _ in range(4)];cov[0][0]="4";cov[1][1]="1"
    path=out/(name+"-uncertainty.json");source_json(db,path,{"schema":"linear-uncertainty/1","measurement_version":m,"covariance":cov,
        "basis":"SYNTHETIC supplied response/intercept variances; other effects unresolved, no confidence or significance claim."})
    freeze_uncertainty(db,"demo2:uncertainty:"+name,m,assay["id"],path)
    path=out/(name+"-process.csv");path.write_text("time,value\n0,7\n12,7\n24,7\n");key=db.objects.add(path)
    tr=db.capture("demo2:trajectory:"+name,"trajectory",{"culture_version":parts["culture"]["id"],"source_digest":key,"variable":"ph","value_unit":"1","time_unit":"h",
        "clock_origin_utc":"2026-10-19T00:00:00Z","alignment":"culture_start","kind_of_observation":"realized","basis":"SYNTHETIC sampled pH only"},artifacts=[key])
    support(db,tr["id"],protocol,{"comparability"})


def seed(db,out,*,enrich=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    protocol=db.capture("demo2:culture-protocol","protocol",{"name":"SYNTHETIC culture procedure"})
    extraction=db.capture("demo2:extraction-protocol","protocol",{"name":"SYNTHETIC extraction"})
    cal=db.capture("demo2:calibration","calibration",{"analyte_id":"demo:product","response_unit":"area","concentration_unit":"mg/L","slope":"2","intercept":"10","min_response":"10","max_response":"10000"})
    context={"medium":"demo2:defined","temperature_c":"30","ph":"7","oxygenation":"shaken-aerobic","vessel":"demo2:flask","batch":"demo2:batch"}
    strains={name:db.capture("demo2:strain:"+name,"strain",{"name":"SYNTHETIC "+name,"genotype_status":"unverified"}) for name in ("A","B")}
    parts=[add_culture(db,out,name+str(i),strains[name],protocol,extraction,cal,context,"1210" if name=="A" else "1010",enrich=enrich) for name in ("A","B") for i in (1,2)]
    cohort=db.capture("demo2:cohort","cohort",{"measurement_versions":[p["measurement"] for p in parts]})
    base=db.capture("demo2:base-policy","policy",{"metric":"titer_g_l","analyte_id":"demo:product","context":{**context,"culture_protocol_version":protocol["id"],"time_h":"24","compartment":"supernatant","extraction_protocol_version":extraction["id"]},"technical_aggregation":"arithmetic_mean","min_biological_replicates":2,"genotype_requirement":"any"})
    process=db.capture("demo2:process-policy","process_policy",{"start_h":"0","end_h":"24","max_gap_h":"12","variables":{"ph":{"unit":"1","minimum":"6.8","maximum":"7.2"}},"basis":"SYNTHETIC observed-point window, no process equivalence"})
    policy=db.capture("demo2:packet-policy","packet_policy",{"base_policy_version":base["id"],"process_policy_version":process["id"],"minimum_culture_units":2,
        "genotype":{"required_regions":["region:1"],"as_of":"2026-10-20T12:00:00Z","max_age_h":"24","minimum_generation":10,"required_scope":"clone"},
        "intended_use":"SYNTHETIC descriptive review only","target_domain":"demo2:flask","basis":"Invented criteria for exercising the software, not a real validation protocol"})
    pool=db.capture("demo2:pool","pool",{"entity_prefix":"demo2:measurement:","filters":{"analyte_id":"demo:product","batch":"demo2:batch"},"boundary":"registered_local_measurements_only"})
    snap=snapshot(db,"demo2:pool-snapshot",pool["id"])
    return {"parts":parts,"cohort":cohort,"policy":policy,"pool":pool,"snapshot":snap,"strains":strains,
            "protocol":protocol,"extraction":extraction,"calibration":cal,"context":context}


def run_demo2(destination):
    out=Path(destination).resolve()
    if out.exists() and any(out.iterdir()):raise IntegrityError("Demo destination must be new or empty")
    out.mkdir(parents=True,exist_ok=True)
    with Instrument(out/"state") as db:
        setup=seed(db,out);packet=freeze(db,"demo2:packet",setup["cohort"]["id"],setup["policy"]["id"],setup["snapshot"]["id"])
        if packet["payload"]["result"]["state"]!="ready_for_scoped_human_review":raise IntegrityError("Synthetic initial packet unexpectedly withheld")
        db.capture("demo2:advance","advance",{"packet_version":packet["id"],"selected_strain_versions":[setup["strains"]["A"]["id"]],"rationale":"SYNTHETIC human choice of the larger descriptive mean; no experiment authorized."})
        w=watch(db,"demo2:watch",packet["id"],setup["snapshot"]["id"],basis="SYNTHETIC pool and evidence watch")
        (out/"initial.html").write_text(render(db,packet["id"]),encoding="utf-8")
        c=db.capture("demo2:strain:C","strain",{"name":"SYNTHETIC new independent candidate","genotype_status":"unverified"})
        newparts=[add_culture(db,out,"C"+str(i),c,setup["protocol"],setup["extraction"],setup["calibration"],setup["context"],"2010") for i in (1,2)]
        changed=watch_status(db,w["id"])
        acknowledge(db,w["id"],changed["fingerprint"],disposition="retain_historical",basis="SYNTHETIC review preserves old decision, does not make it current",actor="synthetic-reviewer")
        acknowledged=watch_status(db,w["id"])
        cohort=db.capture(setup["cohort"]["entity_id"],"cohort",{"measurement_versions":[p["measurement"] for p in setup["parts"]+newparts]},expected=setup["cohort"]["id"],reason="SYNTHETIC explicitly include new candidate")
        snap=snapshot(db,setup["snapshot"]["entity_id"],setup["pool"]["id"],expected=setup["snapshot"]["id"],reason="SYNTHETIC new registered pool")
        updated=freeze(db,packet["entity_id"],cohort["id"],setup["policy"]["id"],snap["id"],expected=packet["id"],reason="SYNTHETIC explicit reassessment")
        db.capture("demo2:advance-C","advance",{"packet_version":updated["id"],"selected_strain_versions":[c["id"]],"rationale":"SYNTHETIC reviewed candidate C; no significance or industrial-transfer inference."})
        (out/"reassessed.html").write_text(render(db,updated["id"]),encoding="utf-8")
        db.capture("demo2:notice-C1","availability",{"measurement_version":newparts[0]["measurement"],"state":"inaccessible","category":"unknown","basis":"SYNTHETIC access/scope uncertainty"})
        withdrawn=status(db,updated["id"])
        results={"data":"SYNTHETIC ONLY; every supporting review is invented","initial_packet":packet["id"],"reassessed_packet":updated["id"],
            "initial_top":"demo2:strain:A","reassessed_top":next(r["strain_id"] for r in updated["payload"]["result"]["summaries"] if r.get("descriptive_rank")==1),
            "pool_growth_alert":changed["requires_reassessment"],"added_candidates":changed["delta"]["added"],
            "acknowledgement_does_not_refresh":acknowledged["requires_reassessment"] and acknowledged["acknowledged"],
            "uncertain_access_reopens":withdrawn["requires_reassessment"],"historical_replay":replay(db,packet["id"]),
            "reassessed_replay":replay(db,updated["id"]),"audit":db.verify()}
        if not all(results[k] for k in ("pool_growth_alert","acknowledgement_does_not_refresh","uncertain_access_reopens")):raise IntegrityError("Synthetic reassessment challenge failed")
        (out/"report.html").write_text(render(db,updated["id"]),encoding="utf-8")
        (out/"results.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
        return results
