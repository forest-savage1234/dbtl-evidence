# The scoped packet workflow

## Inputs and trust boundary

The local filesystem and SQLite administrator are trusted. Actors are supplied names. Hashes establish byte consistency, not acquisition authenticity or reviewer authority. Six assessment dimensions remain independent: arithmetic, measurement, sample identity, replicate independence, comparability and publication version. Supported status is a scoped reviewer assertion requiring retained evidence, not a certificate.

1. Capture exact protocol, strain, culture, sample and calibration versions. Import the supported integrated-peak-area CSV. Raw source rows remain bound to signal and acquisition identity.
2. Register canonical physical culture units and any aliquot/acquisition hierarchy. `unit-assign` links exact material/measurement versions. Assess culture-unit independence. Aliases and technical readings do not create independent n; undeclared aliases remain undetectable.
3. Retain `genotype_observation` records: structured precomputed region calls, exact material and strain, UTC observation, generation, method, clone/population scope and limitations. Assess observation measurement and sample identity. This does not perform sequencing or validate a whole genome.
4. Capture `assay_profile` with structured validation observations, matrix and direct/proxy identity. A measurement assessment of the profile is required separately. Use `uncertainty-freeze` with an explicit four-variable covariance matrix for response, intercept, slope and dilution. This is a conditional first-order model. It does not estimate missing uncertainty, fit calibration or certify analytical validation.
5. Capture realized `trajectory` records and a `process_policy` for the required window, supported variables/units, observed-point bounds and maximum gap. Endpoints must be observed exactly. Assess clock/sensor comparability. No interpolation or scale-transfer inference occurs.
6. Assess each measurement's measurement validity, sample identity and comparability. Open or conflicting dimensions withhold a packet's ranking.
7. Capture a bounded `pool`, its `pool-snapshot`, a `cohort` covering all included registered candidates, the legacy base comparison `policy`, and the new `packet_policy`. This profile requires at least two assessed independent culture units per strain.
8. Create `packet`, inspect `packet-report`, then use `advance` for an explicit current selection and rationale. A packet never performs or authorizes an experiment. Add a watch and poll `watch-list`/`watch-check`; no background process runs automatically.

`dbtl/demo2.py` is an executable complete example of the contracts. The generated JSON/CSV files show their source formats. Its reviews are explicitly synthetic and cannot support real measurements.

## Commands

Use `python3 -m dbtl COMMAND --help` for positional arguments and flags.

| Operation | Commands |
| --- | --- |
| Records and evidence | `capture`, `list`, `show`, `ingest`, `assessment-summary` |
| Pools | `pool-snapshot`, `pool-replay` |
| Explicit watches/reviews | `watch-add`, `watch-check`, `watch-list`, `watch-review` |
| Typed ratios | `quantity-capture`, `derive`, `quantity-replay` |
| Units and assay model | `unit-assign`, `uncertainty-freeze` |
| Literature receipt | `claim-import` |
| Scoped decisions | `packet`, `packet-replay`, `packet-status`, `packet-report`, `advance` |
| Integrity and recovery | `audit`, `backup`, `restore` |
| Synthetic demonstrations | `demo2` (current), `demo` (legacy) |

General `capture` handles observations, trajectories, policies and assessments. `--evidence FILE` retains bytes whose SHA-256 must match the declared source digest. Extra dependencies cannot silently replace required typed references. JSON capture rejects duplicate keys and files over 4 MiB. Revisions require optimistic expected-head checks. Convenience quantity/uncertainty commands create initial records; use general capture or new entity IDs for explicit revisions.

## What the results mean

| Result | Meaning |
| --- | --- |
| `withheld` | At least one scoped requirement is unresolved/conflicting; no strain receives a descriptive rank. Does not establish biological falsity. |
| `ready_for_scoped_human_review` | Recorded evidence and asserted reviews satisfy this explicit profile. The mean is descriptive, without significance or causal inference. |
| `reassessment_pending` | Current registered evidence, assessments, identities, policies or eligible candidates differ from the frozen basis. |
| Successful historical replay | Recorded code/runtime reconstruct the earlier snapshot and result. Says nothing about current eligibility. |
| Blocked historical replay | Restore recorded source/runtime explicitly. Archived code is retained but never auto-executed. |

Packet means average eligible technical readings within mapped physical culture roots, then weight roots equally within a strain. A physical root mapped to multiple strains creates an issue. Withdrawn or unresolved pool candidates cannot enter ranked means; candidate exclusions remain explicit. Missing metadata makes pool eligibility uncertain and withholds ranking. Relevant newly registered results must be reconciled even when absent from the old dependency graph.

The genotype `as_of` is a fixed, explicit review horizon. Current-state checks reconcile registered history under that horizon; they do not advance biological time automatically. Revise the policy for a new horizon. Sensor origin, material linkage and generation remain asserted metadata.

Packet reconstruction uses a read-only view of the registry at its sealed watermark, including historical heads for assessments and mappings. The watermark/journal hash detects history changes but does not establish external evidence completeness. Snapshot selectors retain their algorithm versions. Complete computation sources and exact Python/SQLite versions are pinned for packets and legacy datasets.

## Handoff contract

The implemented consumer accepts only Claim Review `claim-review/1`, `toolVersion=0.3.2-browser` report JSON plus separate matching source bytes. The producing report's SHA-256 and source bytes are retained. Unknown schema/status, omitted upstream open questions, changed bytes or attempted consumer promotion are rejected. The entire producer report remains inspectable. Consumer dimensions stay open because the consumer has not independently established them.

`claim-review-receipt/1` is the stored local receipt. Its compatible code hash identifies the audited contract probe, not proof that an arbitrary report was produced by that code. Imports may be `literature` or `synthetic_fixture`, never local experimental origin. Packet references do not enter culture counts or titer means. The broader `decision-evidence/0.1-draft` remains a historical, unimplemented proposal; no schema-conformance or bidirectional-project claim is made.
