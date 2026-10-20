"""Read-only receipt of Claim Review reports and bytes, without trusting their verdicts."""
import re
from .core import IntegrityError
from .contracts import read_json
from .assessments import DIMENSIONS
from .genotypes import utc

CONTRACT_CODE_SHA256="89fd6fe7ebb04640abfbe50889e75fc803e21ee8cadafbdd72c7beb67d8fb874"
REQUIRED={"schema","toolVersion","spec","digest","sourceWarnings","values","exact","rounded","error",
          "numericalStatus","overallStatus","conditionStatus","conditionTrace","headerTrace","replicates","checks","boundary"}


def inspect(db,report_digest,source_digest):
    report=read_json(db,report_digest,maximum=4*1024*1024);db.objects.verify(source_digest)
    if not REQUIRED<=set(report) or not set(report)<=REQUIRED|{"observedAt"} or report["schema"]!="claim-review/1" or report["toolVersion"]!="0.3.2-browser":
        raise IntegrityError("Unsupported Claim Review report contract")
    if report["digest"]!=source_digest or not re.fullmatch(r"[0-9a-f]{64}",source_digest): raise IntegrityError("Transferred source bytes do not match report fingerprint")
    if "observedAt" in report:utc(report["observedAt"])
    if report["numericalStatus"] not in {"SOURCE_REPLAY","WITHHELD"} or report["overallStatus"]!={"SOURCE_REPLAY":"PARTIAL_SUPPORT","WITHHELD":"REVIEW_REQUIRED"}[report["numericalStatus"]]:
        raise IntegrityError("Unknown or inconsistent producer status; no global verified result is accepted")
    if report["conditionStatus"] not in {"MATCHED","CONFLICT","NOT_DECLARED","NOT_CHECKED"}: raise IntegrityError("Unknown condition status")
    if not isinstance(report["spec"],dict) or not isinstance(report["spec"].get("inputs"),list) or not 1<=len(report["spec"]["inputs"])<=2:
        raise IntegrityError("Missing declared source interpretation")
    for key in ("filename","sheet","op","outputUnit"):
        if not isinstance(report["spec"].get(key),str) or not report["spec"][key].strip(): raise IntegrityError("Missing source location/operation")
    if not isinstance(report["checks"],list) or not report["checks"]: raise IntegrityError("Producer checks must be preserved")
    names=set()
    for check in report["checks"]:
        if not isinstance(check,dict) or set(check)!={"name","status","detail"} or check["status"] not in {"supported","open","conflict"}:
            raise IntegrityError("Unknown upstream assessment status")
        if any(not isinstance(check[k],str) or not check[k].strip() for k in ("name","detail")) or check["name"] in names:
            raise IntegrityError("Ambiguous upstream checks")
        names.add(check["name"])
    for name in ("Measurement history","Experimental context","Publication history"):
        if not any(c["name"]==name and c["status"]=="open" for c in report["checks"]): raise IntegrityError("Required upstream open scientific questions were omitted or promoted")
    if not isinstance(report["replicates"],list): raise IntegrityError("Malformed upstream replication scope")
    for group in report["replicates"]:
        if not isinstance(group,dict) or group.get("independence")!="NOT_ESTABLISHED": raise IntegrityError("Producer replication cannot establish physical independence")
    for key in ("sourceWarnings","values","conditionTrace","headerTrace"):
        if not isinstance(report[key],list): raise IntegrityError("Malformed upstream trace")
    return report


def payload(db,report_digest,source_digest,origin,use_scope):
    if origin not in {"literature","synthetic_fixture"}: raise IntegrityError("Claim handoff is literature/reference evidence, never a local measurement")
    if not isinstance(use_scope,dict) or set(use_scope)!={"intended_use","target_domain"} or any(not isinstance(v,str) or not v.strip() for v in use_scope.values()): raise IntegrityError("Explicit intended use and target domain required")
    upstream=inspect(db,report_digest,source_digest)
    return {"schema":"claim-review-receipt/1","report_digest":report_digest,"source_digest":source_digest,
            "origin":origin,"use_scope":use_scope,"compatible_contract_code_sha256":CONTRACT_CODE_SHA256,
            "upstream":upstream,"consumer_dimensions":{d:{"status":"open","basis":"Producer report retained; this consumer has not independently established this dimension."} for d in DIMENSIONS},
            "boundary":"Untrusted producer assertions retained verbatim. Byte equality and contract checks only; no producer authentication, numerical re-execution, publication-version resolution or permission to pool as local replication."}


def validate_handoff(db,p,deps,artifacts):
    if set(p)!={"schema","report_digest","source_digest","origin","use_scope","compatible_contract_code_sha256","upstream","consumer_dimensions","boundary"} or deps:
        raise IntegrityError("Malformed literature evidence receipt")
    if not {p["report_digest"],p["source_digest"]}<=set(artifacts): raise IntegrityError("Retain both upstream report and source bytes")
    if p!=payload(db,p["report_digest"],p["source_digest"],p["origin"],p["use_scope"]): raise IntegrityError("Handoff changed producer scope or promoted a consumer assessment")


def receive(db,entity_id,report_file,source_file,*,origin,intended_use,target_domain,**kwargs):
    with db.atomic():
        report=db.objects.add(report_file);source=db.objects.add(source_file)
        p=payload(db,report,source,origin,{"intended_use":intended_use,"target_domain":target_domain})
        return db.capture(entity_id,"literature_evidence",p,artifacts=[report,source],**kwargs)
