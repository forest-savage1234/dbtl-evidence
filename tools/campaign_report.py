"""Render and validate the research campaign without third-party dependencies."""
import argparse
from collections import Counter
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def slug(text):
    if re.match(r"^S\d\d\b", text):
        return text[:3].lower()
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()).strip("-")


def inline(text):
    parts, end = [], 0
    for m in re.finditer(r"\[([^\]]+)\]\((https://[^\s)]+)\)", text):
        parts.append(escape(text[end:m.start()]))
        parts.append('<a rel="noreferrer" href="' + escape(m[2], quote=True) + '">' + escape(m[1]) + "</a>")
        end = m.end()
    parts.append(escape(text[end:]))
    result = "".join(parts)
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)
    return re.sub(r"\[(S\d\d(?:,\s*S\d\d)*)\]", lambda m: ", ".join('<a class="cite" href="#' + ref.lower() + '">' + ref + "</a>" for ref in re.findall(r"S\d\d", m[1])), result)


def markdown(text):
    lines = text.splitlines()
    out, toc, i = [], [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("#"):
            m = re.match(r"^(#{1,3})\s+(.+)$", line)
            if not m:
                raise ValueError("Unsupported heading")
            level, title = len(m[1]), m[2]
            id = slug(title)
            if level == 2:
                toc.append((id, title))
            out.append(f'<h{level} id="{id}">' + inline(title) + f"</h{level}>")
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", c) for c in row):
                    rows.append(row)
                i += 1
            if not rows or len({len(row) for row in rows}) != 1:
                raise ValueError("Malformed table")
            body = '<div class="table-wrap"><table><thead><tr>'
            body += "".join("<th>" + inline(c) + "</th>" for c in rows[0]) + "</tr></thead><tbody>"
            body += "".join("<tr>" + "".join("<td>" + inline(c) + "</td>" for c in row) + "</tr>" for row in rows[1:])
            out.append(body + "</tbody></table></div>")
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append("<li>" + inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("#", "|", "- ")):
            paragraph.append(lines[i].strip())
            i += 1
        out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
    return "\n".join(out), toc


class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.resources = [], [], []
        self.tables = self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag in {"script", "img", "iframe", "link"}:
            self.resources.append((tag, attrs))
        self.tables += tag == "table"
        self.scripts += tag == "script"


def validate():
    ledger = json.loads((ROOT / "evidence/campaign/sources.json").read_text())
    backlog = json.loads((ROOT / "evidence/campaign/backlog.json").read_text())
    sources = {s["id"] for s in ledger["sources"]}
    assert len(sources) == len(ledger["sources"]) == 18
    counts = Counter(s["access"] for s in ledger["sources"])
    assert counts["full_text_sections"] == ledger["counts"]["full_text_sections"] == 10
    tasks = {t["id"]: t for t in backlog["tasks"]}
    assert len(tasks) == len(backlog["tasks"]) == 18
    def visit(id, stack):
        assert id not in stack, "Backlog dependency cycle"
        for dep in tasks[id]["depends_on"]:
            assert dep in tasks
            visit(dep, stack | {id})
    for id, t in tasks.items():
        visit(id, set())
        assert set(t["sources"]) <= sources
        assert t["status"] == "proposed"
    report = (ROOT / "docs/INDUSTRY_CAMPAIGN.md").read_text()
    assert set(re.findall(r"\bS\d\d\b", report)) <= sources
    assert "SOURCE_LEDGER" not in report
    all_probes = []
    for name, n in [("dbtl", 6), ("claim", 5)]:
        p = json.loads((ROOT / f"evidence/campaign/{name}-probes.json").read_text())
        assert len(p["results"]) == n
        assert all(r["expectation_met"] is True for r in p["results"])
        all_probes.extend(r["id"] for r in p["results"])
    assert len(set(all_probes)) == 11
    for t in tasks.values():
        assert set(t["probes"]) <= set(all_probes)
    original = json.loads((ROOT / "evidence/campaign/dbtl-probes.json").read_text())
    for path, expected in original["production_source_sha256"].items():
        assert sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    schema = json.loads((ROOT / "docs/decision-evidence-0.1-draft.schema.json").read_text())
    assert schema["properties"]["schema"]["const"] == "decision-evidence/0.1-draft"
    dimensions = {"arithmetic", "measurement", "sample_identity", "replicate_independence", "comparability", "publication_version"}
    assert set(schema["properties"]["assessments"]["required"]) == dimensions
    assert schema["$defs"]["assessment"]["properties"]["status"]["enum"] == ["supported", "conflict", "open", "out_of_scope"]
    assert "overallStatus" not in schema["properties"] and "verified" not in schema["properties"]
    return {"sources": 18, "inspected_full_text_sections": 10, "probes": 11,
            "proposed_work_packages": 18, "production_fingerprints_unchanged": True,
            "schema_check": "JSON syntax and campaign invariants; no full JSON Schema conformance validator"}


CSS = """
:root{--ink:#162f2b;--muted:#536962;--teal:#12675b;--line:#d6e0d8;--paper:#fffef9;--soft:#eaf1eb}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.62 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--teal);text-underline-offset:3px;overflow-wrap:anywhere}
.banner{padding:28px max(5vw,24px);border-bottom:1px solid var(--line);letter-spacing:.12em;font-size:12px;font-weight:700}
.layout{display:grid;grid-template-columns:220px minmax(0,1000px);gap:48px;max-width:1360px;margin:0 auto;padding:40px 28px}
aside{position:sticky;top:24px;height:calc(100vh - 48px);overflow:auto;font-size:12px;line-height:1.45}
aside a{display:block;margin-bottom:13px;text-decoration:none;color:var(--muted)}
aside strong{display:block;letter-spacing:.1em;margin-bottom:20px}
main{min-width:0}h1{font:600 clamp(36px,4vw,56px)/1.12 Georgia,serif;letter-spacing:-.025em;margin:6px 0 22px;max-width:850px}
h2{font:600 30px/1.25 Georgia,serif;margin:64px 0 20px;padding-top:12px;border-top:2px solid var(--line)}
h3{font-size:18px;line-height:1.4;margin:34px 0 12px}p{max-width:88ch;margin:0 0 18px}li{margin:7px 0}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0 28px}
.card{background:var(--soft);padding:17px;border-radius:5px}.card strong{display:block;font:600 32px/1.1 Georgia,serif}.card span{display:block;font-size:12px;color:var(--muted);margin-top:8px}
.notice{border-left:4px solid var(--teal);background:var(--soft);padding:18px 20px;font-size:14px;margin-bottom:30px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:4px;margin:24px 0 30px}
table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.5;min-width:680px}th,td{padding:13px 14px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
th{background:var(--soft);font-weight:650}tr:last-child td{border-bottom:0}td:first-child{font-weight:550;min-width:95px}
.cite{font-size:12px;white-space:nowrap}footer{border-top:1px solid var(--line);padding:28px 5vw;font-size:12px;color:var(--muted)}
@media(max-width:1000px){.layout{grid-template-columns:1fr;gap:16px}aside{display:none}.cards{grid-template-columns:repeat(2,1fr)}}
@media print{aside,.banner{display:none}.layout{display:block;padding:0}body{font-size:10pt}h1{font-size:30pt}h2{font-size:18pt;break-after:avoid;margin-top:28px}h3{break-after:avoid}.table-wrap{overflow:visible}table{min-width:0;font-size:8pt}.cards{grid-template-columns:repeat(4,1fr)}a{color:inherit}tr{break-inside:avoid}}
"""


def render(destination):
    result = validate()
    content, toc = markdown((ROOT / "docs/INDUSTRY_CAMPAIGN.md").read_text())
    nav = "".join('<a href="#' + id + '">' + escape(title) + "</a>" for id, title in toc)
    cards = '<div class="cards">' + "".join('<div class="card"><strong>' + str(n) + '</strong><span>' + label + "</span></div>" for n, label in [
        (18, "scientific sources"), (11, "synthetic boundary probes"), (69, "passing reference tests"), (18, "proposed work packages")]) + "</div>"
    content = content.replace("</h1>", "</h1>" + cards + '<div class="notice"><strong>Decision integrity, with explicit limits.</strong> Two separate complementary instruments. A literature-grounded campaign and reproducible software audit; industrial efficacy remains unproven.</div>', 1)
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Metabolic Engineering · Decision Integrity Campaign</title><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'none\'; script-src \'none\'; base-uri \'none\'"><style>' + CSS + '</style></head><body><div class="banner">FOREST SAVAGE · RESEARCH & ENGINEERING · 20 OCTOBER 2026</div><div class="layout"><aside><strong>CAMPAIGN CONTENTS</strong>' + nav + "</aside><main>" + content + '</main></div><footer>Research assessment · source access and limitations disclosed · synthetic probes are not laboratory validation</footer></body></html>'
    inspection = Inspector()
    inspection.feed(html)
    assert len(inspection.ids) == len(set(inspection.ids)), "Duplicate HTML anchor"
    assert not inspection.resources and not inspection.scripts
    assert all(href[1:] in inspection.ids for href in inspection.links if href.startswith("#"))
    assert inspection.tables == 8, inspection.tables
    destination = Path(destination).resolve()
    destination.write_text(html, encoding="utf8")
    return {**result, "html": str(destination), "tables": inspection.tables,
            "internal_links_valid": True, "external_resources": 0, "bytes": destination.stat().st_size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    print(json.dumps(render(parser.parse_args().output), indent=2))
