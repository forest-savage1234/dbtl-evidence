# DBTL Evidence Instrument · v1.0 research release

Research software by **Forest Savage**.

One local application for versioned product-titer comparisons and correction
review. It coordinates a SQL registry, a content-addressed file store,
dependency queries, numerical replay, and a readable offline report.

This release is a tested foundation for a specific assay workflow, **not a
complete solution to metabolic-engineering data management or a laboratory-
validated production platform**. Read [SCOPE.md](SCOPE.md) before using real data.

## Complementary scientific instruments

This project is maintained separately from Forest Savage's
[Claim Review literature checker](https://github.com/forest-savage1234/casefile-provenance-demo/tree/main/claim-review)
and the [ME2026 research records](https://github.com/forest-savage1234/metabolic-engineering-forensics).

| Instrument | Main question | Evidence boundary |
| --- | --- | --- |
| [Claim Review](https://forest-savage1234.github.io/casefile-provenance-demo/claim-review/) | Can this published quantitative claim be reconstructed from the declared source data and calculation? | Source files, specified cells, numerical relationships, declared conditions, and unresolved support |
| DBTL Evidence Instrument | Can this experimental comparison be reproduced, and which recorded outputs need reassessment when its supporting evidence changes? | Versioned samples, cultures, calibrations, measurements, comparison policies, datasets, and decisions |

The projects have independent implementations and release histories. Their
shared aim is stricter scientific data integrity. No live connector, shared
database, or automatic transfer between the applications is implemented.
The [companion-project design](docs/COMPANION_PROJECTS.md) describes a proposed
evidence handoff and the checks needed before implementing it.

## Run immediately

Requires Python 3.11+ and SQLite 3.38+ with JSON support. No third-party runtime
packages, accounts, network connection, or installation are required to run from
the extracted source directory. Python/SQLite releases outside the tested Linux
environment have not been qualified.

```bash
python3 -m dbtl --version
python3 -m dbtl demo --output my-synthetic-demo
python3 -m unittest discover -v
```

Open `my-synthetic-demo/report.html` in a browser. The demo refuses to overwrite
a populated destination. The bundle also contains a ready-made example under
`examples/synthetic-demo/`, including three reports and the retained registry.

The deliberate calibration correction changes the descriptive winner from A
(0.60 g/L) to B (0.51 g/L); A recalculates to 0.30 g/L. Both have two declared
culture units. Technical repeats are averaged within each culture before the
strain-level mean. Two unsuitable measurements remain visible as exclusions.
The earlier result and decision are preserved; two affected outputs receive
review findings. These are synthetic demonstration outcomes, not lab results.

## Main operations

Global `--root` and `--actor` options precede the subcommand. Operators are
asserted names; this local release does not authenticate users.

```bash
python3 -m dbtl --root my-state init
python3 -m dbtl --root my-state --actor researcher capture protocol:1 protocol protocol.json --reason "Initial protocol capture"
python3 -m dbtl --root my-state ingest peak_areas.csv
python3 -m dbtl --root my-state list --kind measurement
python3 -m dbtl --root my-state audit
python3 -m dbtl --root my-state reviews
python3 -m dbtl --root my-state report --output report.html
python3 -m dbtl --root my-state backup --output snapshot.zip
python3 -m dbtl restore snapshot.zip restored-state
```

Use `python3 -m dbtl <command> --help` for the exact arguments for `cohort`,
`freeze`, `replay`, `impact`, `decide`, `review`, `recalibrate`, and
`refresh-cohort`. Capture uses JSON objects and exact version references.
Revisions require `--expected <current-version-id>` and an explicit reason.
`--evidence <local-file>` retains evidence bytes; extra construction inputs use
`--dependency recipient=<strain-version>` and other documented roles.

## What the release proves

- Histories cannot be overwritten through the normal API or ordinary SQL DML.
- Retained artifacts are rehashed before a dataset calculation/replay.
- Raw signal values are checked against their claimed retained CSV row.
- Current calculations refuse superseded input versions.
- Historical calculations use exact saved inputs and the recorded implementation.
- Correction findings identify downstream current outputs and explain a path.
- Dataset membership includes excluded candidates so they remain in the graph.
- Technical acquisitions do not become independent biological sample counts.
- Acknowledging a review does not make stale evidence current.
- Committed state can be backed up, verified, and restored without arbitrary ZIP extraction.

These are demonstrated software behaviors over synthetic fixtures. They do not
prove correct physical labeling, validated calibration, causal attribution,
independence of cultures, statistically significant improvement, or faster DBTL
cycles in a laboratory.

## Data contract

See [the contract](docs/DATA_CONTRACT.md) for identifiers, units, required
context, calibration convention, supported corrections, and exclusions.
[The architecture](docs/ARCHITECTURE.md) separates implemented components from
future integrations. [The research survey](docs/RESEARCH.md) reviews 25
systems/standards and documents close prior art. [The challenge log](docs/CHALLENGES.md)
records defects found, fixes, evidence, and residual gaps at each milestone.

The entry interface is a CLI plus JSON/CSV, with a read-only HTML report. A
guided wet-lab interface and usability evaluation remain necessary to address
the biologist/developer workflow gap.

## Release evidence and history

The local Git tags are `v0.1`, `v0.2`, …, `v0.9`, `v1.0`. Each gate writes its
test IDs, outcome, environment, and code hashes under `evidence/` before the
corresponding commit. They are actual sequential implementations, not ten
labels for one final code snapshot.

Citation metadata are in [CITATION.cff](CITATION.cff). Licensing of this new
project has not been selected; related projects and their dependencies retain
their own existing license terms.

If the source bundle contains `history.bundle`, recover the history with:

```bash
git clone history.bundle reconstructed-history
git -C reconstructed-history tag --list
```

To verify the source archive itself, hash every file listed in
`PACKAGE_MANIFEST.json`. Hashes provide consistency, not an independent
signature or proof of authorship. Generated state is replayable only under the
recorded source and exact Python/SQLite versions; incompatible runtimes are
reported as blocked rather than silently reinterpreted.

Run `python3 tools/benchmark.py` to repeat the local benchmark. The saved result
is small-scale single-process evidence, not a forecast of omics throughput or
a comparison with an optimized existing platform.
