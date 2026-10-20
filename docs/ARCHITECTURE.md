# Implemented architecture and extension boundaries

| Component | Implemented here | Production extension requiring validation |
| --- | --- | --- |
| Transactional registry | SQLite, immutable JSON records, relational identity, optimistic revisions, atomic imports | PostgreSQL backend, schema migrations, tenancy, access control, operational recovery |
| Evidence bytes | Streaming capture, SHA-256 addressing, fsync, exclusive publication, verification | Remote object storage, version IDs, access policy, lifecycle, redundancy |
| Identity/domain contracts | Exact version references, strain/culture/sample separation, multi-input activities | Lab-specific identity reconciliation, barcode integration, ontology mapping |
| Adapter | Strict exported peak-area CSV with source-row verification | Validated LC-MS/RNA-seq/sensor/robot/ELN/LIMS adapters |
| Analytical computation | Linear calibration and descriptive titer summaries with explicit policy | Columnar analytical engine, distributed scale, batch models, uncertainty propagation |
| Dependency service | Recursive SQL reachability, independent oracle tests, bounded path display | Incremental materialized projection if real workloads justify it; dedicated graph engine only after benchmarking |
| Replay | Historical inputs, retained source, environment fingerprints, deterministic recomputation | Environment containers/lockfiles, upgraded-pipeline migration, cross-platform qualification |
| Review | Source-version changes, downstream targets, explicit human dispositions | Alerts, policy-specific triage, cross-system acknowledgements, usability studies |
| Scientist interface | CLI, JSON/CSV input, script-free HTML report | Guided capture/comparison UI, spreadsheet roundtrip, accessibility testing |
| Portability | Source ZIP/manifest, Git history bundle, verified state backup/restore | Signed releases, distribution, monitored deployments, offsite restore drills |

`core.py` is the registry; `storage.py` retains bytes; `domain.py` defines the
small contracts; `ingest.py` binds signals to raw source rows; `graph.py` answers
dependency questions; `calc.py` defines the numerical operation; `datasets.py`
freezes/replays it; `review.py` records reassessment; `audit.py` checks local
consistency; `backup.py` preserves committed state; `cli.py` and `report.py`
provide access. `demo.py` generates the explicitly synthetic counterfactual.

The JSON dependency array is part of the immutable record and its hash. An SQL
view exposes edges for graph queries. This avoids separately mutable graph and
relational authorities in the reference implementation. At much larger scale,
indexing/materializing a rebuildable edge projection will likely be necessary;
this is an untested future optimization, not a performance promise.

The instrument deliberately does not reproduce EDD, ICE, Benchling, TeselaGen,
Synthace, or other platforms' full functionality. A lab deployment should
evaluate embedding the workflow in an existing platform or using its interfaces
before adopting another permanent source of truth. No external repository or
service was changed by this work.
