"""Create a stand-alone readable overview from actual release evidence and demo."""
import argparse
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def inline(text):
    output, end = [], 0
    for match in re.finditer(r"\[([^\]]+)\]\((https://[^\s)]+)\)", text):
        output.append(escape(text[end:match.start()]))
        output.append("<a rel='noreferrer' href='" + escape(match.group(2), quote=True) + "'>" + escape(match.group(1)) + "</a>")
        end = match.end()
    output.append(escape(text[end:]))
    return "".join(output)


def markdown(text):
    lines, output, index = text.splitlines(), [], 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            output.append("<div class='scroll'><table>" + "".join("<tr>" + "".join("<" + ("th" if n == 0 else "td") + ">" + inline(c) + "</" + ("th" if n == 0 else "td") + ">" for c in row) + "</tr>" for n, row in enumerate(rows)) + "</table></div>")
            continue
        if line.startswith("#"):
            output.append("<h3>" + inline(line.lstrip("# ")) + "</h3>")
        elif line:
            paragraph = [line]
            while index + 1 < len(lines) and lines[index+1].strip() and not lines[index+1].lstrip().startswith(("#", "|")):
                index += 1; paragraph.append(lines[index].strip())
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
        index += 1
    return "".join(output)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True)
    args = parser.parse_args()
    gates = [json.loads(p.read_text()) for p in ROOT.glob("evidence/v*.json")]
    gates.sort(key=lambda r: tuple(map(int, r["release"].split("."))))
    final = next(r for r in gates if r["release"] == "1.0")
    report = (ROOT / "examples/synthetic-demo/report.html").read_text()
    report = re.sub(r"<h1>.*?</h1>", "<h2>Demonstrated correction and reassessment</h2>", report, count=1)
    heading = """<p class='eyebrow'>WORKING SOFTWARE · RESEARCH RELEASE 1.0</p><h1>DBTL Evidence Instrument</h1>
    <p class='lead'>One integrated local instrument for defensible titer comparisons and explainable correction review.</p>
    <div class='cards'><div><strong>10</strong><span>sequential release gates</span></div><div><strong>""" + str(final["tests_run"]) + "</strong><span>passing automated checks</span></div><div><strong>25</strong><span>systems and standards surveyed</span></div></div>" + """
    <div class='notice'><b>What 1.0 means:</b> a tested foundation for one exported peak-area assay workflow. It does not establish production readiness, universal DBTL coverage, laboratory efficacy, or novelty.</div>
    <p>Read the source bundle's README for execution. This report is self-contained, requires no login, and contains synthetic demonstration results only.</p>"""
    report = report.replace("<main>", "<main>" + heading, 1)
    more = "<h2>Sequential release evidence</h2><p>Each version was implemented, tested, committed, and tagged before advancing. The source bundle includes the full local history and per-gate evidence.</p><div class='scroll'><table><tr><th>Version</th><th>Tests</th><th>Gate</th></tr>" + "".join("<tr><td>" + escape(g["release"]) + "</td><td>" + str(g["tests_run"]) + "</td><td>" + escape(g["status"]) + "</td></tr>" for g in gates) + "</table></div>"
    more += "<details><summary>Integrity challenges, repaired defects, and open production gates</summary>" + markdown((ROOT / "docs/CHALLENGES.md").read_text()) + "</details>"
    more += "<details><summary>Research survey: 25 systems and standards, with primary sources</summary>" + markdown((ROOT / "docs/RESEARCH.md").read_text()) + "</details>"
    more += "<details><summary>Implemented architecture and extension boundaries</summary>" + markdown((ROOT / "docs/ARCHITECTURE.md").read_text()) + "</details>"
    report = report.replace("<footer>", more + "<footer>", 1)
    report = report.replace("</style>", ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:28px 0}.cards div{padding:22px;background:#e3ece6;border-radius:8px}.cards strong{display:block;font-size:36px;line-height:1.2}.cards span{font-size:13px;color:#45615b}a{color:#0f665b;text-underline-offset:3px}</style>", 1)
    Path(args.output).write_text(report, encoding="utf-8")
    print(json.dumps({"overview": str(Path(args.output).resolve()), "tests": final["tests_run"], "gates": len(gates)}))


if __name__ == "__main__": main()
