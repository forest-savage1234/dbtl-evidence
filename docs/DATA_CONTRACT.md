# v1.0 scientific and software contract

## Identities and lineage

Stable entity IDs contain 1–128 ASCII letters, digits, `.`, `_`, `:`, or `-`.
Version IDs are distinct immutable references. Entity kind cannot change.
Revision writes require the exact current predecessor. Dependencies refer to
existing version IDs and carry roles; both payload and dependencies are hashed
together. The evidence derivation graph is acyclic by insertion order. This
does not require metabolic reaction/regulation networks to be acyclic.

Kinds include intended design, physical strain, construction activity, culture,
sample, protocol, calibration, measurement, import, cohort, comparison policy,
dataset, decision, review, and a generic model reference. Models are reference
records only: model training, inference, and validation are not implemented.

Construction activities require one recipient strain. Donors can be strains or
designs; vectors are designs; protocols are protocol versions. Derived strains
can point to the activity through `built_by`. Operator-asserted verified
genotypes require a retained artifact; the software does not validate sequencing
evidence or infer that an intended design was realized.

## Peak-area CSV adapter

UTF-8 (optional BOM); exact header order:

```csv
measurement_id,sample_version,calibration_version,analyte_id,response,response_unit,dilution,qc,quantification,technical_replicate_id,run_id
```

References must identify exact sample/calibration versions. `response_unit` is
`area`. Supported calibration output units are `g/L`, `mg/L`, and `ug/L`.
`dilution` is a positive multiplier. Numeric fields use finite decimal strings;
binary floats, infinity, NaN, locale commas, and extreme exponents are rejected.
The adapter supports at most 100,000 measurements per import. Parsing retains
at most four raw-row lookup caches in an instance; it is not a streaming
multiomics analytical engine.

QC is `pass`, `fail`, or `unreviewed`. Quantification status is `quantified`,
`below_loq`, `above_uloq`, or `unreviewed`. Only passing, quantified responses
within the operator-declared calibration range can contribute. Censored values
are excluded with reasons, never converted to zero.

The acquisition identity consists of stable physical sample entity, analyte,
run, and technical replicate. A renamed acquisition cannot be imported as a
second measurement, including after a sample metadata revision. Reimports
return the original measurement versions in original file-row order, even
after recalibration. A changed source requires explicit revision rather than
silent upsert. Malformed imports roll back all registry rows; already captured
but unreferenced objects may remain and are reported as warnings.

## Calibration and metric

The exact convention is:

`response = slope × concentration + intercept`

`titer_g_l = ((response − intercept) / slope) × dilution × unit_conversion`

The slope must be positive; calibration and measurement analyte/unit must
match. Calculations use Decimal precision 50 and half-even rounding. Range
limits are supplied in response units. Calibration fitting, nonlinear/internal-
standard methods, analytical validation, instrument drift correction,
measurement uncertainty, and source authenticity are not inferred.

The metric is **titer**, not yield or productivity. The release does not record
the required substrate-consumption or production-time denominator for those
other metrics. It refuses policies claiming those unsupported metrics.

## Comparison policy

An immutable policy names the analyte, metric, minimum culture count, genotype
eligibility, arithmetic aggregation of technical repeats, and all ten supported
context fields: medium, temperature in °C, pH, oxygenation, vessel, batch,
culture protocol version, sampling time in hours, compartment, and extraction
protocol version. Numeric context compares decimal values; other context uses
exact identifiers/text. This deliberately favors explicit exclusions over
guessing that two labels are equivalent.

Missing/mismatched context produces a visible exclusion. Cross-batch pooling
is not implemented. No supported policy implies that these ten fields exhaust
all scientifically relevant confounders. Medium lots, evaporation, inoculum,
biomass, instrument effects, extraction recovery, and unrecorded process
conditions can still invalidate interpretation. Additional metadata belongs
under namespaced `extensions`; adding it does not make the current comparison
algorithm account for it.

Technical acquisitions first average within a declared physical culture entity.
Culture means receive equal weight in a strain's mean and sample SD. The
software trusts the declared culture identity; separate identifiers do not
prove true biological independence. Minimum culture count is an eligibility
rule, not a power calculation. Rankings are descriptive; equal means share
rank. No confidence intervals, hypothesis tests, or causal effect estimates
are generated.

## Corrections, replay, and review

Raw signal/acquisition fields must match the retained source row. An explicit
revision can change calibration, sample association, QC, or quantification
interpretation while preserving the earlier record and reason. A raw response
change requires newly retained source bytes supporting that response; the
automatic CSV import path does not silently revise an existing measurement.
The convenience recalibration operation only advances the same calibration
entity. Other supported revisions use `capture` with an exact predecessor.

A dataset freezes cohort membership (including excluded candidates), policy,
computed result, all package source files, hashes, and Python/SQLite versions.
Replay uses historical versions and refuses implementation/runtime mismatch.
Archived Python is never automatically executed. Upgrade migration/replay under
changed semantics is not implemented.

Review targets are current datasets, decisions, and generic model references.
A superseded ancestor creates a finding keyed by target/old/current versions.
The queue contains one finding per such combination, not one per graph path.
An explanation gives a shortest path; long displayed paths are explicitly
truncated with `path_complete=false` and the full `total_steps`. Reachability
still covers every descendant. CLI `impact --path-limit` controls display depth.

A human can retain an output as historical or retire it, with a note. This
records a disposition without asserting current scientific validity. A later
source correction creates a new obligation. Explicit recomputation creates new
measurement/cohort/dataset/decision versions. Previously independent new
results affect a frozen analysis only after an explicit cohort revision.

## Backups and trust

Backups hold a committed SQLite snapshot and all referenced artifacts. Active
uncommitted transactions are refused. Restore checks allowed paths, duplicate
members, symlinks, hashes, schema, and local audit before exposing the new
directory. Maximum uncompressed backup size is 1 GiB in this release.

The trusted boundary is a local user's filesystem. Hashes and SQL triggers are
consistency mechanisms, not signed chain-of-custody, authenticated authorship,
protection from a privileged administrator, an offsite backup strategy, or
regulatory compliance. There is no multi-tenant access control or network API.
