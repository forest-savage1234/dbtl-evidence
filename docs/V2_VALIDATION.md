# v2.0 validation assessment

Status: local synthetic software evaluation. No laboratory efficacy study, independent scientific adjudication, controlled usability trial or industrial deployment has been completed. A version label is not a maturity certificate.

## Campaign crosswalk

The original 18-work-package backlog remains unchanged under `evidence/campaign/backlog.json`. A local implementation is not closure of a multi-project or real-data acceptance gate.

| Campaign | Delivery in this repository | Remaining acceptance boundary |
| --- | --- | --- |
| C00 decision/corpus | Scoped titer-review decision and adversarial synthetic corpus | Twelve-case public coverage pilot, independent adjudication and holdout registration not completed |
| C01 dimensions | v1.1 assessments and v1.9 receipt preserve separate statuses | Claim Review producer schema unchanged; scientific criteria need external review |
| C02 denominator | v1.4 typed local quantity basis; biomass cannot be substrate yield | No Claim Review estimand editor, carbon balance or inferred source semantics |
| C03 estimators | v1.4 explicit paired mean-of-ratios versus ratio-of-means | Checker itself unchanged; repeated measures/hierarchical estimators absent |
| C04 pools | v1.2 bounded registry selector and snapshots | No upstream discovery/completeness or ontology integration |
| C05 reassessment | v1.3 pool/availability watches; v2 packet reconciliation includes new reviews | Polling only; real upstream event reliability and integrations untested |
| C06 genotype | v1.6 scoped source calls and external-assessment requirements | No read alignment, variant calling, sequence authentication or whole-genome/stability validation |
| C07 units | v1.5 canonical root/aliquot/acquisition and assessed n | Undeclared aliases, inoculum/shared-control blocks, cross-paper experiment resolution unresolved |
| C08 process | v1.8 observed pH/DO/temperature windows and gaps | Feed/volume mass balance, calibrated clocks and industrial transfer remain unvalidated |
| C09 assay | v1.7 structured observations, direct/proxy/censoring boundaries | No raw chromatogram integration, fitting, chemical-ID, standards/recovery/drift validation |
| C10 uncertainty | v1.7 exact-rational first-order propagation and joint-covariance contrast | No covariance estimation, full uncertainty budget, rank sensitivity or hierarchical inference |
| C11 handoff | v1.9 genuine pinned producer-core fixture into report/source receipt | One-way only; no producer authentication, re-execution, semantic mapping or bidirectional project round trip |
| C12 corrections | Availability scope and explicit review; bibliographic correction does not imply numeric failure | No automatic publisher monitoring or general change-classification service |
| C13 comparison | Protocol prepared | No blinded comparative participant/task evaluation |
| C14 reliability | Local rollback/restart, checksums, backup/restore, clean-source execution | Representative workload SLOs, backpressure, distributed faults and multi-user operations untested |
| C15 ML utility | Evidence can remain a model dependency | No training export, leakage/domain-shift validation or recommendation engine |
| C16 laboratory | Field protocol prepared | No partner/data acquisition-to-decision study completed |
| C17 release assessment | Ten gated increments, retained test identities, limits and complete history | External validation/signed releases remain open; no industrial release claim |

## Evidence to inspect

`evidence/v1.1.json` through `evidence/v2.0.json` record the actual sequential gates. Tests check independent numerical/set oracles, malformed contracts, missing context, source corruption, wrong genotype material/scope/time, nominal versus realized processes, shared covariance, pool changes, human-review semantics, history and recovery. `examples/claim-review-synthetic/provenance.json` identifies the pinned producer-core execution; tests consume its report/source without installing or changing Claim Review.

The final gate also creates `examples/scoped-demo/` and records its summary. Its reviewer support is invented to test routing and withholding, not evidence of biological or analytical validity. Existing `examples/synthetic-demo/` and `evidence/campaign/` preserve earlier releases and limitations. A newer code release does not silently rewrite the earlier audit or treat its 69-test result as the present test count.

## Integrity findings during this series

The v1.6 gate exposed an import/packaging error before tagging; the module was relocated and the full suite rerun. Integration challenges found that new conflicting assessment entities needed packet reconciliation beyond ordinary dependency revisions. A later challenge found that a refreshed snapshot could otherwise allow withdrawn readings back into a mean; packet computation now filters by current pool eligibility and retains explicit exclusions. Independent physical mappings are checked globally across strains, not only per strain. All are software defects or scope issues; none establish falsity of a scientific study.

## Release boundary

No claim of exhaustiveness, novelty, cost reduction, measured DBTL acceleration or superiority to an existing platform follows. Current infrastructure is an append-only SQLite reference, local files, Python standard library, CLI and static reports. It is not an omics lakehouse, metabolic network inference engine, LIMS, instrument controller or production multi-tenant service. Exact code/runtime restoration is required for numerical replay across source changes. The field protocol is the next acceptance gate.
