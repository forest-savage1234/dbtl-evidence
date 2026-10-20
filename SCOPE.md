# Release contract

This is a local research instrument, not a complete solution to all DBTL data
management. One integrated application can coordinate several components. A
single database cannot replace lab measurements, instrument drivers, identity
discipline, biological interpretation, and organizational adoption.

The v1.0 target is a reproducible, versioned comparison of one calibrated product
titer assay and correction-driven review of its recorded downstream decisions.
It is not a production-qualified enterprise platform. All fixtures are synthetic.

SQLite is the executable, dependency-free reference backend. PostgreSQL, remote
object storage, distributed analytics, live ELN/LIMS adapters, authentication,
instrument control, and validated omics parsers are not implemented by this
release. There are no performance claims for hundreds of millions of rows.

An append-only record and checksum establish local consistency and byte
integrity; they do not prove biological truth, original acquisition authenticity,
trusted identity of the operator, or resistance to an administrator who rewrites
the entire database and hashes. The local filesystem is a trusted boundary.

## Incremental gates

| Version | Delivered boundary | Integrity challenge |
| --- | --- | --- |
| 0.1 | Immutable identities, revisions, typed dependency roles | overwrite, missing dependency, stale revision, rollback |
| 0.2 | Content-addressed evidence artifacts | tampered bytes, missing evidence, partial writes |
| 0.3 | Strict, atomic CSV adapter and domain contracts | wrong identity, duplicate import, malformed numbers |
| 0.4 | Multi-input construction and dependency traversal | wrong roles, cycles, diamond paths |
| 0.5 | Explicit comparison policy and biological-unit summaries | unit errors, missing context, pseudoreplication |
| 0.6 | Frozen datasets and deterministic replay | changed implementation, changed artifacts, changed input |
| 0.7 | Correction impact, reasons, and human review | missed descendants, excessive flags, new corrections |
| 0.8 | Command-line workflow and offline readable report | unsafe rendering, misleading status, usability |
| 0.9 | Adversarial audit and measured local performance | concurrency, corrupted registry, independent graph oracle |
| 1.0 | Reproducible package, backup/restore, complete local workflow | clean extraction, missing dependencies, portability |

The numeric versions are bounded milestones. Passing them does not establish
lab deployment readiness or commercial superiority.

## v2.0 extension

The reference now implements the ten increments in README.md and docs/releases/v1.1.md through v2.0.md. The primary `packet`/`advance` workflow enforces bounded review requirements; legacy `freeze`/`decide` retain their narrower descriptive scope. Typed ratios are a separate arithmetic utility and do not extend packet ranking beyond calibrated titer. Separate scientific assessments remain reviewer assertions.

See docs/V2_WORKFLOW.md for exact contracts and docs/V2_VALIDATION.md for completed versus open gates. The field protocol has been prepared, not executed. Industrial efficacy, real sample authenticity, whole-genome validation, complete uncertainty, process equivalence, background discovery and production qualification remain unestablished. A fixed genotype as-of horizon does not advance automatically with wall-clock time. Claim Review remains unchanged; only the bounded report/source receiver is implemented here.
