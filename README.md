# DBTL Evidence Instrument · v2.0 research release

Research software for Forest Savage's metabolic-engineering evidence campaign.

Create a scoped comparison, retain its exact evidence and calculation, and find when new or changed registered evidence requires reassessment. **This is a local research instrument, not a complete solution to DBTL or an industrially validated product.**

The application coordinates a SQLite registry, retained files, graph queries and numerical computations. SQL remains useful for identity and transactions. Replacing it cannot establish physical sample identity, analytical validity, scientific interpretation or laboratory adoption.

## Run the complete synthetic campaign

Python 3.11+ and SQLite 3.38+ with JSON support; no third-party runtime packages, account or network needed. The actual release gate records the tested Python/SQLite versions. Other runtime/platform combinations remain unqualified until their checks run.

```bash
python3 -m dbtl --version
python3 -m dbtl demo2 --output my-scoped-demo
python3 -m unittest discover -v
```

Open `my-scoped-demo/report.html`. All data, observations and supporting reviews in this demonstration are **invented**. Initially A has the larger descriptive mean. Two newly registered C cultures reopen the old decision; explicit reassessment includes C. An unresolved access notice then reopens the new packet. Historical packets remain replayable under their recorded code/runtime. Acknowledgment does not refresh evidence.

The bundled `examples/scoped-demo/` retains this campaign. `python3 -m dbtl demo` runs the older calibration-correction demonstration, which reverses its descriptive ranking. Historical v1.0 bundled datasets may require the v1.0 code/runtime to replay; their preserved records remain readable.

## What changed from 1.0

| Release | Implemented boundary |
| --- | --- |
| 1.1 | Separate reviewer assessments of six evidence dimensions |
| 1.2 | Bounded registered-measurement pools and reconstructable snapshots |
| 1.3 | Membership/availability changes and explicit review of watched outputs |
| 1.4 | Source-bound quantity basis, units and paired versus pooled ratios |
| 1.5 | Physical culture/aliquot/acquisition mappings and assessed independence |
| 1.6 | Material-, time-, generation- and region-scoped genotype observations |
| 1.7 | Assay evidence, proxy/censoring boundaries and conditional covariance propagation |
| 1.8 | Realized sensor trajectories, clock scope, observation gaps and explicit limits |
| 1.9 | One-way Claim Review report-and-source receipt, preserving upstream limitations |
| 2.0 | Frozen decision packets, explicit human selection, current-state reconciliation, CLI and recovery |

Each increment is a separate tested commit/tag. Gate receipts list test IDs, outcomes, runtime and source hashes in `evidence/v*.json`. The number 2.0 denotes this implemented scope, not laboratory readiness.

## The primary v2 workflow

Global `--root` and `--actor` precede subcommands. Actors and reviews are assertions, not authenticated identities.

```bash
python3 -m dbtl --root my-state init
python3 -m dbtl --root my-state ingest peak-areas.csv
python3 -m dbtl --root my-state capture protocol:1 protocol protocol.json --reason "Initial capture"
python3 -m dbtl --root my-state list --kind measurement
python3 -m dbtl --root my-state packet --help
python3 -m dbtl --root my-state packet-status PACKET_VERSION
python3 -m dbtl --root my-state packet-replay PACKET_VERSION
python3 -m dbtl --root my-state packet-report PACKET_VERSION --output packet.html
python3 -m dbtl --root my-state watch-list
python3 -m dbtl --root my-state audit
python3 -m dbtl --root my-state backup --output snapshot.zip
python3 -m dbtl restore snapshot.zip restored-state
```

Replace uppercase version placeholders with returned exact version IDs. [The workflow guide](docs/V2_WORKFLOW.md) explains required records, statuses and commands. Capture revisions require the exact current `--expected` version and a reason. Generic JSON/CSV entry remains an engineering interface; a guided scientist interface has not been evaluated.

`packet` enforces scoped evidence gates; `advance` records an explicit human choice from a current eligible packet. `freeze` and `decide` retain the narrower legacy v1 behavior for compatibility and **do not enforce v2 gates**. A successful legacy decision is not a v2-qualified selection.

## Separate, complementary projects

[Claim Review](https://github.com/forest-savage1234/casefile-provenance-demo/tree/main/claim-review) remains unchanged and independently executable. [ME2026 research records](https://github.com/forest-savage1234/metabolic-engineering-forensics) remain separate. No code or unrelated workflows from those projects are merged here.

`claim-import` receives a supported Claim Review report and its original source bytes. It retains open/conflicting checks verbatim and keeps all consumer scientific dimensions open. It neither re-executes the checker nor authenticates the producer. Literature receipts are reference-only in packets; they cannot increase local culture counts. See [the companion boundary](docs/COMPANION_PROJECTS.md).

## Research and unclosed gates

The [industry campaign](docs/INDUSTRY_CAMPAIGN.md) is the preserved v1.0 baseline audit: 18 scientific sources and a targeted review, not an exhaustive census. The earlier [survey](docs/RESEARCH.md) covers 25 systems/standards and close prior art. [v2 validation status](docs/V2_VALIDATION.md) maps the campaign to delivered software and remaining work. [The field protocol](docs/FIELD_VALIDATION_PROTOCOL.md) specifies the comparative evaluation still required.

Passing tests demonstrates bounded software behavior on synthetic data. It does not establish genuine independent cultures, source authenticity, valid assays, whole-genome correctness, process equivalence, statistical superiority, industrial transfer or faster laboratory cycles. First-order uncertainty is conditional on supplied covariance; omitted effects remain unresolved. Pool coverage is registered history only. No live upstream discovery, background alerts, ELN/LIMS integration, authentication, remote storage or industrial omics-scale qualification is implemented.

## Recover and publish

The source archive includes file hashes and complete local Git history. Recover it with:

```bash
git clone history.bundle reconstructed-history
git -C reconstructed-history tag --list
```

No standalone GitHub publication is claimed. The intended `forest-savage1234/dbtl-evidence` repository was unavailable to the connection, which cannot create repositories. [Publishing instructions](docs/PUBLISHING.md) preserve the independent project and all tags. Licensing for this new project has not been selected; third-party projects retain their existing terms.
