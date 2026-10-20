> Historical broader draft. v1.9 implements a narrower one-way Claim Review report/source receipt, documented in [V2_WORKFLOW.md](V2_WORKFLOW.md). This draft schema remains unimplemented and is not accepted by that importer.

# Evidence handoff: 0.1 specification draft

Status: proposed contract for C01/C11 of INDUSTRY_CAMPAIGN.md. Neither application currently implements this importer/exporter. This document is not a third product, a claim of interoperability, or a scientific validation certificate.

## Project boundary

Claim Review exports a literature-evidence object containing its exact source and bounded assessment. DBTL Evidence may use that object as an upstream literature reference after a future adapter implements the required checks. It must not register the imported result as a locally measured culture/sample merely because the arithmetic replayed.

Both applications remain independently executable and separately versioned. The schema lives here for review; a later agreed release should be mirrored or referenced by pinned identity without sharing application internals.

## Required concepts

The accompanying JSON Schema identifies origin, producing application and code fingerprint, source bytes and locations, declared quantity semantics, six independent assessment dimensions, and intended use. The example is synthetic, not an extracted scientific result.

Every assessment has a status, a basis and source references. The dimensions are arithmetic, measurement, sample identity, replicate independence, comparability and publication version. They do not collapse into a global verified flag.

A supported arithmetic assessment establishes only that declared numerical operation in its declared scope. It does not establish measurement validity, interpretation of the source, independent cultures or relevance to the target process. A supported comparability assessment must name the criterion, target domain and evidence; merely importing a claim cannot establish it.

Record quantity identity as well as dimensions. Include the meaning of denominators and aggregation in basis/estimator. The draft uses explicit strings to avoid pretending a complete biological ontology exists. A production profile will need typed, versioned terms and unit semantics validated for its bounded use.

Hash matches establish retained byte identity. Producer hashes identify code but do not authenticate its author. Source URIs do not authorize network access or retrieval of protected material. The consumer must retain or obtain permitted bytes and verify their digest without silently substituting a new version.

## Consumer invariants for future implementation

1. Reject an unknown schema version, malformed identity, mismatched digest, unresolved source reference or unsupported quantity profile.
2. Preserve every open, conflict and out-of-scope assessment verbatim. A local reassessment is a new linked record with its own evidence, actor and rationale, not an overwrite of the producer's assessment.
3. Require explicit, reviewable mappings between external strain/sample terms and local material identities. An asserted name match is not physical authentication.
4. Preserve literature, local experiment, simulation and synthetic-fixture origins. Never count simulation or a reused publication as independent new experimental replication.
5. Enforce intended-use and target-process boundaries. A result about one host, assay or process does not become eligible in another merely because a unit matches.
6. Preserve fixed-source versus bounded-pool versus unknown coverage. The consumer creates its own pool membership and eligibility assessment; it does not invent producer coverage.
7. A changed source, estimator, policy, mapping or relevant pool membership creates a new version and a reassessment event for affected use.
8. Schema conformance is a structural check. It cannot certify that a basis statement is scientifically adequate or true.

## Required adverse tests

- A valid product/biomass division cannot be imported as supported product/substrate yield.
- A source fingerprint mismatch blocks handoff.
- A proxy measurement cannot become direct concentration without retained calibration/validation evidence.
- Renaming one aliquot three times does not establish three independent cultures.
- A formula or observation limit remains explicit after export/import.
- An unknown or omitted assessment dimension does not default to supported.
- A producer's PARTIAL_SUPPORT cannot become a consumer-wide verified result.
- A new matching published observation outside a previous dependency closure changes the appropriate bounded pool.
- A harmless author-name correction changes publication metadata without asserting numerical invalidity.
- Historical imports remain inspectable even if later source access is lost.

## Validation status

The schema and one synthetic example can be structurally checked. They do not demonstrate a working application-to-application round trip. Full conformance tests, semantic profiles, schema migration, authority/mapping rules and operational security remain C11 work. Production integration must wait for those gates.
