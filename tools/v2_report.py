"""Render an evidence-limited release assessment from receipts and verified Git tags."""
import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TITLES=["Separate assessments","Bounded evidence pools","Pool and availability watches","Typed source-bound ratios","Physical experimental units","Scoped genotype observations","Assay evidence and covariance","Realized process trajectories","Separate-project receipt","Integrated decision packets"]


def history():
    gates=[];checks=0
    for version,title in zip(["1."+str(i) for i in range(1,10)]+["2.0"],TITLES):
        p=json.loads((ROOT/"evidence"/("v"+version+".json")).read_text())
        if p["status"]!="passed" or p["failures"] or p["skipped"] or len(p["passed_tests"])!=p["tests_run"]:raise ValueError("Incomplete release gate: "+version)
        commit=subprocess.check_output(["git","rev-parse","v"+version],cwd=ROOT,text=True).strip()
        retained=json.loads(subprocess.check_output(["git","show","v"+version+":evidence/v"+version+".json"],cwd=ROOT))
        if retained!=p:raise ValueError("Gate receipt differs from tag")
        for name,expected in p["source_hashes"].items():
            content=subprocess.check_output(["git","show","v"+version+":"+name],cwd=ROOT)
            if sha256(content).hexdigest()!=expected:raise ValueError("Tagged source differs: "+name)
            checks+=1
        gates.append({"version":version,"title":title,"tests":p["tests_run"],"commit":commit,"python":p["python"],"sqlite":p["sqlite"],"seconds":p["elapsed_seconds"]})
    for a,b in zip(gates,gates[1:]):subprocess.run(["git","merge-base","--is-ancestor",a["commit"],b["commit"]],cwd=ROOT,check=True)
    return gates,checks


def render():
    gates,checks=history();latest=json.loads((ROOT/"evidence/v2.0.json").read_text());demo=latest["demonstration"]
    sources=json.loads((ROOT/"evidence/campaign/sources.json").read_text())["sources"]
    rows="".join("<tr><td>"+escape(g["version"])+"</td><td>"+escape(g["title"])+"</td><td>"+str(g["tests"])+"</td><td><code>"+g["commit"][:12]+"</code></td></tr>" for g in gates)
    refs="".join("<li><a href='"+escape(s["url"],quote=True)+"'>"+escape(s["id"]+" · "+s["title"])+"</a><br><small>"+escape(s["access"]+" · "+s["limit"])+"</small></li>" for s in sources)
    findings=[("New independent evidence","Two new C cultures outside the old dependency graph reopen the A decision. Explicit reassessment considers C."),
              ("Historical versus current","Both frozen packets reconstruct under the recorded code/runtime. Unknown access subsequently reopens the later packet."),
              ("Review does not refresh","Acknowledgment retains history; it does not remove evidence changes or make a stale packet eligible."),
              ("Separate projects","The unchanged pinned Claim Review core produced a synthetic report consumed by DBTL. Upstream open/conflicting checks survive; consumer dimensions remain open."),
              ("Independent checks","Exact-rational numerical and covariance oracles, seeded set membership, tampered bytes, malformed input, recovery and clean-package execution are tested.")]
    finding_html="".join("<article><h3>"+escape(a)+"</h3><p>"+escape(b)+"</p></article>" for a,b in findings)
    summary={"scope":"local synthetic research release","gates":gates,"tagged_source_hashes_checked":checks,"demonstration":demo,
             "external_validation":"not completed","github_publication":"pending; standalone repository unavailable to connection, repository creation unsupported"}
    html="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'none'"><title>DBTL Evidence 2.0 · release assessment</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f6f5ef;color:#193b3c;font:16px/1.65 system-ui,sans-serif}main{max-width:1120px;padding:50px 28px 90px;margin:auto}header{padding:35px 0 36px;border-bottom:2px solid #275857}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:700;color:#476f6b}h1{font:600 clamp(38px,6vw,68px)/1.06 Georgia,serif;max-width:800px;margin:22px 0}h2{font:600 30px/1.2 Georgia,serif;margin:48px 0 18px}h3{font-size:17px;margin:0 0 8px}.lead{max-width:850px;font-size:19px}.notice{padding:20px 24px;background:#efe0c1;border-left:5px solid #a86b18;margin:26px 0}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0}.metric{border:1px solid #bed0c8;padding:18px;background:white}.metric strong{display:block;font:600 38px Georgia,serif}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}article{background:#fff;padding:22px;border-top:3px solid #477d72}article p{margin-bottom:0}table{width:100%;border-collapse:collapse;background:white}td,th{padding:13px 16px;text-align:left;border-bottom:1px solid #d6dfd9}th{background:#e4ede6}.scroll{overflow-x:auto}small{font-size:13px;color:#516863}li{margin:12px 0}a{color:#226357}code{font-size:13px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#e6ece6;padding:20px;font-size:12px}footer{border-top:1px solid #9aaca1;margin-top:45px;padding-top:18px;font-size:13px}details{margin-top:24px}@media(max-width:650px){main{padding:25px 18px}.metrics,.grid{grid-template-columns:1fr}td,th{padding:10px}.lead{font-size:17px}}@media print{main{padding:0}article,table,.notice{break-inside:avoid}details{display:none}a{color:inherit}}
</style></head><body><main><header><p class="eyebrow">Forest Savage · 20 October 2026 · research software</p><h1>DBTL Evidence 2.0</h1><p class="lead">A scoped decision can retain its evidence, explain its limits and reopen when registered evidence changes.</p><p>Ten sequential implementations from 1.1 to 2.0. Claim Review remains a separate, unchanged project.</p></header>"""
    html+="<div class='notice'><strong>What this release establishes</strong><br>Tested local software behavior on invented records and reviews. It does not establish laboratory benefit, scientific validity, production readiness or a complete solution to metabolic-engineering data management.</div>"
    html+="<div class='metrics'><div class='metric'><strong>10</strong>tested, tagged increments</div><div class='metric'><strong>"+str(latest["tests_run"])+"</strong>passing tests in the final gate</div><div class='metric'><strong>18</strong>scientific sources in the prior targeted audit</div></div>"
    html+="<h2>The engineering result</h2><p>Keep SQL for identities, transactions and version order; retain evidence files separately and expose one evidence workflow. Database selection cannot establish material identity, assay validity, biological interpretation or organizational adoption. The highest-leverage hypothesis is defensible decision review over an evolving bounded evidence pool.</p><div class='grid'>"+finding_html+"</div>"
    html+="<h2>The actual iteration record</h2><p>Every row is a distinct commit/tag with its own test identities and source hashes. "+str(checks)+" recorded source hashes were checked against their respective tagged Git objects. Tags are sequential ancestors; this is consistency evidence, not independent authorship attestation.</p><div class='scroll'><table><tr><th>Version</th><th>Delivered boundary</th><th>Passing tests</th><th>Local commit</th></tr>"+rows+"</table></div>"
    html+="<h2>Where both instruments still fall short</h2><table><tr><th>Instrument</th><th>Delivered</th><th>Still open</th></tr><tr><td>Claim Review</td><td>Its pinned core still reconstructs declared source calculations and reports partial support.</td><td>Scientific estimand editor, paired estimators, physical-unit resolution and independent assay/context validation were not added to the checker.</td></tr><tr><td>DBTL Evidence</td><td>Typed quantities, scoped observations, assessed unit mappings, conditional covariance, sampled process limits, packet history and reassessment.</td><td>Real instrument validation, authenticated material/review identities, upstream completeness, guided scientist interface, live ELN/LIMS adapters and industrial-scale qualification.</td></tr><tr><td>Combined workflow</td><td>One-way report/source receipt with no scientific promotion or local replication.</td><td>Producer authentication, independent numerical re-execution, semantic cross-process mapping and bidirectional project round trip.</td></tr></table>"
    html+="<h2>The campaign to close the gap</h2><ol><li>Freeze one laboratory decision, exact assay/process scope, error taxonomy and permitted sources. Screen at least twelve public cases as a coverage pilot; do not call it an efficacy sample.</li><li>Use independent scientific adjudicators and experiment-family holdouts. Preserve unresolved evidence and disagreements.</li><li>Compare the present workflow, a configured existing platform and that platform with this layer. Include setup, curation, false alerts, serious unsupported assertions, missed changes and review time.</li><li>Replay a permitted real acquisition-to-decision chain; inject corrections, independent new candidates, access loss and recovery failures against predeclared objectives.</li><li>Publish outcomes and limits. Stop the standalone-product direction if an existing extension gives equivalent integrity with less burden.</li></ol><p>These external studies are prepared, not completed. No benefit estimate or industrial success is inferred from synthetic tests. The archive contains the full field protocol and an eighteen-work-package completion crosswalk.</p>"
    html+="<h2>Important operating limits</h2><p>Reviewer support is asserted. Genotype calls are precomputed, scoped and tied to a fixed review horizon. First-order uncertainty is conditional on supplied covariance and omits unidentified effects. Observed process points do not establish behavior between samples or transfer across scale. Descriptive ranks are neither significance nor robust-rank evidence. Pools cover registered history, with polling rather than background discovery. Legacy freeze/decide commands retain v1 scope and do not enforce v2 packet gates.</p><p>Historical numerical replay requires the recorded code and exact runtime; archived code is never auto-executed. This release was tested with Python "+escape(latest["python"])+" and SQLite "+escape(latest["sqlite"])+" on the recorded Linux environment.</p>"
    html+="<h2>Use and publication</h2><pre>python3 -m dbtl demo2 --output my-scoped-demo\npython3 -m unittest discover -v\n\n# Recover all local commits and tags from the source archive:\ngit clone history.bundle reconstructed-history</pre><p>The separate GitHub repository was unavailable to the connection and repository creation is unsupported. Publication is pending. The source archive retains all commits, tags, tests, documents and synthetic evidence; Claim Review code is not merged or duplicated into it.</p>"
    html+="<h2>Scientific source ledger</h2><p>The preserved review is targeted, not exhaustive or preregistered. Access limits below constrain its claims. No new article was experimentally reproduced and no ME2026 case was re-adjudicated by this release.</p><ol>"+refs+"</ol><details><summary>Machine-readable release verification summary</summary><pre>"+escape(json.dumps(summary,indent=2))+"</pre></details><footer>DBTL Evidence · Forest Savage · local research release 2.0. No laboratory, industrial-efficacy, novelty or misconduct conclusion follows from these software checks.</footer></main></body></html>"
    return html,summary


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args();path=Path(a.output)
    if path.exists():raise SystemExit("Report destination already exists")
    html,summary=render();path.write_text(html,encoding="utf-8")
    print(json.dumps({"report":str(path.resolve()),"gates":len(summary["gates"]),"final_tests":summary["gates"][-1]["tests"],"tagged_source_hashes_checked":summary["tagged_source_hashes_checked"]}))


if __name__=="__main__":main()
