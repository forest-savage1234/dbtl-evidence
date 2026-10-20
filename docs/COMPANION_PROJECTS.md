# Separate instruments, complementary evidence workflows

Forest Savage's scientific-literature checker and the DBTL Evidence Instrument
address connected parts of scientific data integrity. Keeping separate code,
repositories, version histories, evidence records, and scientific claims makes
their individual scope inspectable.

## Current projects

| Project | Current role | Source |
| --- | --- | --- |
| Claim Review | Browser-based reconstruction of declared numerical relationships and source context for quantitative scientific claims | [Browser source](https://github.com/forest-savage1234/casefile-provenance-demo/tree/main/claim-review), [application](https://forest-savage1234.github.io/casefile-provenance-demo/claim-review/) |
| Metabolic Engineering Forensics | ME2026 comparative protocol, four original case manifests, a Python manifest verifier, and recorded research findings | [Research repository](https://github.com/forest-savage1234/metabolic-engineering-forensics) |
| DBTL Evidence Instrument | Versioned experimental identities, calibrated titer comparisons, saved calculations, and correction-driven reassessment | This repository |

Claim Review is the complementary numerical-checking instrument; the ME2026
repository preserves the related study record. The checker happens to be hosted
inside another repository's `claim-review/` directory. This project does not
import the other workflows hosted beside it.

The descriptions above were checked against the existing repositories' current
READMEs on 20 October 2026. Original ME2026 case findings, later browser results,
and this instrument's synthetic evaluations remain distinct evidence records.

## How the scientific questions connect

The literature checker starts with a reported value and a declared interpretation
of a source artifact. It asks how far the numerical reconstruction and recorded
context support that value. This is useful when published values are reused as
engineering inputs or comparisons.

The DBTL instrument starts with recorded experimental data. It reconstructs a
bounded comparison and tracks dependencies so that corrections can trigger
reassessment. Its present workflow supports calibrated product titer, not an
arbitrary formula, whole-paper audit, yield, or productivity calculation.

Together, the research direction covers both reuse of existing literature and
preservation/reassessment of newly generated experimental evidence. The software
does not yet connect these workflows automatically. Promise at this level is
an engineering hypothesis; the combined approach still needs comparative
evaluation with real data and scientists.

## Proposed handoff boundary — not an implemented integration

Exchange a versioned evidence package, rather than coupling either application's
private database or copying a verdict. A future adapter would need the following
fields and explicit validation:

| Information | Required validation |
| --- | --- |
| Claim identity and exact publication/source version | Resolve the intended claim and source state without treating a title or URL as a unique immutable identity |
| Source artifact bytes and SHA-256 | Rehash transferred bytes; preserve availability and licensing restrictions; do not infer acquisition authenticity |
| Exact source location and interpretation | Retain sheet/cell/table/figure references and distinguish measured observations from derived summaries |
| Numeric value, units, and metric | Validate dimensions, calibration convention, rounding, and any denominator; a titer cannot silently become yield or productivity |
| Calculation specification and implementation version | Recompute with the recorded supported algorithm; reject unknown or changed semantics |
| Experimental identity and context | Map design, physical strain, culture, sample, assay, and calibration explicitly; missing context remains unresolved |
| Dependency closure and exclusions | Include all comparison candidates and recorded exclusions, with reasons; unlinked new evidence requires explicit review |
| Verification scope and unresolved requirements | Carry the actual checks performed and their limits; numerical agreement must not become a claim of full experimental verification |

A laboratory datum and a published claim might refer to the same underlying
observation without sharing the same entity identity or scientific context.
Matching hashes establish byte equality only. Any identity reconciliation and
decision to pool evidence require an inspectable rule or human review.

## Independence requirements

- Each instrument must run and be tested without installing or executing the other.
- Each retains its own supported calculation types and verification semantics.
- A failed or unavailable adapter must not prevent independent use of either tool.
- Corrections preserve source versions and earlier analyses in the receiving tool.
- No paper's result is declared incorrect merely because support is incomplete.
- No broad superiority, novelty, or laboratory-benefit claim follows from synthetic tests alone.
- Existing code, published artifacts, and third-party licenses remain with their owners and terms.

The first integration evaluation should use a small licensed or synthetic
package, exercise unit/context mismatches and source corrections, and compare
both applications' independent outputs before adding any automatic workflow.
