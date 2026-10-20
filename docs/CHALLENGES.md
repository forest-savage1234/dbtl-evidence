# Integrity challenge ledger

Each milestone was implemented, tested, committed, and tagged before the next.
Passing checks establish the bounded behaviors below. They do not establish
universal correctness. Exact test IDs and source hashes are in `evidence/v*.json`.

| Version | Passing gate | Challenge and observed outcome | Residual boundary |
| --- | --- | --- | --- |
| 0.1 | 8 tests | Stale optimistic edits, missing/duplicate dependencies, attempted SQL overwrite, batch rollback, NaN, and modified Python input all exercised | Generic roles do not yet establish biological meaning |
| 0.2 | 13 tests | Corrupted/missing artifacts and symlink/path substitutions rejected; duplicate capture retains one exact object | No authenticated acquisition or privileged-attacker protection |
| 0.3 | 20 tests | Strict schema/units/identity, whole-import rollback, and single-row idempotency exercised | Review identified an O(n²) duplicate-acquisition scan; later multirow/revision coverage exposed further idempotency gaps |
| 0.4 | 25 tests | Replaced scan with an expression-index lookup; prevented duplicate acquisition across sample revisions; diamond reachability, missing upstream bytes, and construction roles exercised | Biological labeling remains a supplied assertion |
| 0.5 | 35 tests | Known-unit calculations, censored/range exclusions, context mismatch, minimum culture counts, and technical-replicate collapse exercised | Context list is deliberately incomplete; no biological validity, uncertainty, or statistical inference |
| 0.6 | 42 tests | Corrected calibration leaves historical replay intact but blocks current reuse; changed implementation/bytes and forged dataset result rejected | Initially pinned a named computation-file list; v0.9 broadened it to every package source file |
| 0.7 | 49 tests | Exact downstream target set and paths, explicit disposition, new-correction reopening, and recalibration/refresh exercised | Independent new reports require explicit cohort membership; review does not prove a conclusion false |
| 0.8 | 53 tests | Synthetic ranking reversal demonstrated end-to-end; script/HTML injection text escaped; clean CLI roundtrip and overwrite refusal checked | CLI and read-only report do not solve wet-lab interface adoption |
| 0.9 | 61 tests | Independent graph oracle (20 sampled starts over a seeded 160-node DAG), exact-fraction calibration oracle (15 cases), concurrent edits, source-row binding, deep paths, and corruption tested | Small synthetic cases and a local benchmark cannot establish omics-scale performance |
| 1.0 | See final gate | Added backup/restore roundtrip, tampered archives, traversal, existing-destination and uncommitted-state refusal, clean-source-package execution, and tied-rank coverage | Production and laboratory qualification remain open |

## Defects actually found and repaired

- The first CSV duplicate check scanned all measurements per row. The v0.4
  release uses an expression index and stable sample identity across versions.
- Reimport originally enumerated all revisions that pointed to an import and
  sorted them by random version ID. Adversarial multirow/recalibration coverage
  found duplicated, reordered historical outputs. The v0.9 path returns only
  initial versions in original source-row order.
- A preserved file hash alone did not bind a manually revised response to the
  claimed raw row. v0.9 verifies raw signal/acquisition fields and requires new
  raw bytes for a changed signal; tests reject unsupported signal changes.
- The first strengthened audit parser stopped trigger definitions at an
  internal semicolon. Five tests reported false integrity failures. Inspection
  showed truncated expected trigger SQL; separate trigger/view parsing repaired
  it, and the 60-test suite then passed. This was an audit implementation defect,
  not evidence of corrupted measurement histories.
- Keeping full path copies for every descendant has quadratic memory cost on a
  long chain. v0.9 stores predecessor links and bounds displayed explanations,
  retaining complete descendant coverage and explicit truncation metadata.
- Opening an unsupported database initially applied schema setup before checking
  its version. v0.9 preflights existing databases read-only and refuses unsupported
  or incomplete schema before schema writes.
- SQLite backup from a source connection holding an active write transaction
  can stall. The release uses a separate read snapshot under a registry write
  reservation and refuses an already-uncommitted user transaction.

## Open gates that block a production claim

1. A participating laboratory, representative real assay files, and independent
   assessment of sample mapping and calibration validity.
2. Comparative evaluation against the lab's existing platform, with setup and
   ongoing curation included; the research survey identifies close prior art.
3. A guided scientist interface and actual usability/accessibility evaluation.
4. Validated instrument/ELN/LIMS adapters and standards-conformance tests.
5. Representative high-volume workloads, concurrent users, operational failure
   injection, monitoring, recovery, and data retention policy.
6. Authentication, authorization, scientific review roles, release signing,
   trusted acquisition, and audited administrative boundaries if required.
7. Measurement uncertainty, stronger comparability assessment, batch effects,
   confounding, and statistically justified decisions where scientifically needed.

The next highest-value step is a blinded real-data comparison with an existing
solution, not adding more version numbers or claiming the whole field is solved.
