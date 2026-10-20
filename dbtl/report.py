"""Readable, self-contained, script-free local report. All record text is escaped."""
from html import escape
import json

from .core import IntegrityError
from .datasets import replay
from .graph import outdated_sources
from .review import findings


def e(value):
    return escape(str(value), quote=True)


def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join("<th>" + e(h) + "</th>" for h in headers) + "</tr></thead><tbody>" + "".join("<tr>" + "".join("<td>" + e(v) + "</td>" for v in row) + "</tr>" for row in rows) + "</tbody></table></div>"


def render_report(db, *, title="DBTL evidence report"):
    audit = db.verify()
    sections = ["<p class='eyebrow'>DBTL EVIDENCE · LOCAL RESEARCH INSTRUMENT</p><h1>" + e(title) + "</h1>",
                "<p class='lead'>Reconstruct the comparison. Preserve the earlier result. Review what changed.</p>",
                "<div class='notice'>Scope: calibrated product titer from exported peak areas. All demo data are synthetic. Local integrity and numerical replay do not establish biological truth or experimental comparability beyond the declared policy.</div>"]
    sections.append("<h2>Registry integrity</h2><p class='" + ("good" if audit["ok"] else "bad") + "'>" + ("Local consistency checks passed" if audit["ok"] else "Integrity failed — results are withheld") + "</p>")
    sections.append("<pre>" + e(json.dumps(audit, indent=2)) + "</pre>")
    if audit["ok"]:
        queue = findings(db, include_acknowledged=True)
        pending = [f for f in queue if not f["acknowledged"]]
        sections.append("<h2>Correction review</h2><p>" + str(len(pending)) + " pending findings against current outputs. Acknowledgement records a human disposition; it does not make old evidence current.</p>")
        if queue:
            sections.append(table(["Output", "Changed source", "State", "Dependency steps"], [
                [f["target_entity"], f["source_entity"], f["disposition"] or "needs review", len(f["path"])] for f in queue]))
            for f in queue:
                sections.append("<details><summary>" + e(f["target_entity"] + " ← " + f["source_entity"]) + "</summary><pre>" + e(json.dumps(f, indent=2)) + "</pre></details>")
        for dataset in db.versions("dataset"):
            p = dataset["payload"]
            stale = outdated_sources(db, dataset["id"])
            try:
                replay(db, dataset["id"])
                replay_text = "Numerical replay passed"
            except IntegrityError as exc:
                replay_text = "Replay blocked: " + str(exc)
            sections.append("<h2>" + e(dataset["entity_id"]) + " · revision " + str(dataset["revision"]) + "</h2><p>" + e(replay_text) + ". " + ("Historical evidence has superseded inputs." if stale else "No superseded dependencies detected.") + "</p>")
            sections.append(table(["Strain", "Mean titer (g/L)", "Biological units", "Sample SD (g/L)", "Descriptive rank"], [
                [s["strain_id"], s["mean_g_l"], s["biological_n"], s["sample_sd_g_l"] or "undefined", s.get("rank", "ineligible")]
                for s in p["result"]["summaries"]]))
            sections.append("<p>" + e(p["result"]["interpretation"]) + "</p>")
            sections.append("<details><summary>Declared comparison policy and eligibility</summary><pre>" + e(json.dumps(db.get(p["policy_version"])["payload"], indent=2)) + "</pre></details>")
            if p["result"]["excluded"]:
                sections.append("<details><summary>Excluded measurements (" + str(len(p["result"]["excluded"])) + ")</summary>" + table(["Measurement version", "Reasons"], [[r["measurement_version"], "; ".join(r["reasons"])] for r in p["result"]["excluded"]]) + "</details>")
            sections.append("<details><summary>Exact evidence and computation identifiers</summary><pre>" + e(json.dumps({"dataset_version": dataset["id"], "result_sha256": p["result_sha256"], "algorithm_manifest": p["algorithm_manifest"]}, indent=2)) + "</pre></details>")
        decisions = db.versions("decision")
        if decisions:
            sections.append("<h2>Recorded decisions</h2>" + table(["Decision", "Revision", "Selected strains", "Rationale"], [[d["entity_id"], d["revision"], ", ".join(db.get(v)["entity_id"] for v in d["payload"]["selected_strain_versions"]), d["payload"]["rationale"]] for d in decisions]))
        reviews = db.versions("review")
        if reviews:
            sections.append("<h2>Preserved review dispositions</h2>" + table(["Reviewer assertion", "Disposition", "Reason"], [[r["actor"], r["payload"]["disposition"], r["payload"]["note"]] for r in reviews]))
    sections.append("<footer>Historical replay, current eligibility, and scientific validity are separate assessments. Calibration coefficients and sample identities are operator-supplied. No authentication, remote adapters, or enterprise scale qualification is provided by this release.</footer>")
    style = """body{margin:0;background:#f4f3ee;color:#172f35;font:16px/1.6 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:52px 24px}h1{font-size:clamp(30px,5vw,52px);line-height:1.15;letter-spacing:-1.8px;max-width:850px}h2{margin-top:42px;font-size:25px}.eyebrow{font-size:12px;font-weight:750;letter-spacing:2px;color:#466460}.lead{font-size:21px;max-width:760px}.notice{padding:18px 22px;border-left:4px solid #bd8747;background:#fff5e4;max-width:900px}.good{color:#146644;font-weight:700}.bad{color:#aa2530;font-weight:700}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;background:#fff;margin:16px 0 24px;font-size:14px}td,th{text-align:left;padding:12px 15px;border-bottom:1px solid #d7e0dc;vertical-align:top}th{background:#e3ece6}details{background:#fff;margin:12px 0;padding:14px 18px;border-radius:6px}summary{cursor:pointer;font-weight:650}pre{overflow:auto;font:12px/1.6 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere}footer{margin-top:48px;padding-top:22px;border-top:1px solid #bbc9c2;font-size:13px;color:#526765}"""
    return "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; script-src 'none'\"><title>" + e(title) + "</title><style>" + style + "</style><main>" + "".join(sections) + "</main></html>"
