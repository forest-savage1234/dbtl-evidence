# Existing solutions and engineering decision

Research date: 20 October 2026. Scope: public first-party documentation, official
repositories, and original research papers. This is a broad desktop survey, not
a certified exhaustive market census, patent search, or hands-on evaluation of
licensed platforms. Undocumented functionality remains **unknown**, not absent.
Product descriptions are capability claims by their vendors, not independently
measured benefits. No claims of novelty or commercial superiority are made.

## Findings that changed the design

1. The premise that relational models cannot handle multiple parents or graph
   queries is false. PostgreSQL documents recursive traversal and indexed JSONB.
   DataJoint explicitly combines relational dependencies, code, and object storage.
2. A unified DBTL/data platform is established territory: ICE/EDD/ART,
   TeselaGen, Benchling, and Synthace cover substantial pieces already.
3. Correction-sensitive provenance has close prior art. FAIR Data Pipeline
   documents issue tracking against data/code and provenance reporting. Its
   original paper describes provenance-driven quality management. This
   materially weakens a claim that downstream review after changed evidence is
   a fundamentally new software idea.
4. A graph engine does not resolve missing calibration, wrong sample identities,
   unknown experimental conditions, or incompatible units. Conversely, a
   provenance DAG is not a model of biological causality or a metabolic network.
5. The defensible contribution to evaluate is a domain-specific workflow and
   its measured effects: faithful titer comparisons, explicit exclusions,
   preserved historical results, and explainable reassessment. Benefit and
   distinctiveness remain hypotheses until comparative laboratory evaluation.

## Capability evidence and build/reuse decisions

Each row describes only functionality supported by the cited primary source.
“Test” means a future comparative experiment, not an assertion of a missing
competitor feature. Prices, licensing suitability, and deployment effort were
not audited.

| # | System or standard | Documented capability | Consequence for this instrument |
| --- | --- | --- | --- |
| 1 | [EDD](https://github.com/JBEI/edd) and [original paper](https://pubs.acs.org/doi/10.1021/acssynbio.7b00204) | Standardized experimental data/metadata, visualization, and export | Prefer a future EDD adapter to replacing its repository; test correction review interoperability |
| 2 | [ICE](https://github.com/JBEI/ice) | Biological parts registry, characterization, access, sharing | Treat registry identity and construct records as upstream inputs |
| 3 | [ART original paper](https://www.nature.com/articles/s41467-020-18008-4) | Machine-learning recommendations for metabolic engineering | Keep prediction/experiment selection separate from evidence eligibility; no ART integration is implemented |
| 4 | [ICE–EDD–ART workflow paper](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2021.612893/full) | Integrated multiomics storage, visualization, and learning workflow | Demonstrates that an integrated solution can contain multiple specialized tools |
| 5 | [Benchling Registry](https://www.benchling.com/registry), [lineage enforcement](https://help.benchling.com/hc/en-us/articles/9684225761677-Enforce-Lineage-for-Entity-Relationships) | Biological relationships and constrained entity linkages | Do not claim complex lineage is unsolved; test exact-version result propagation via export/API |
| 6 | [Benchling schemas](https://docs.benchling.com/docs/schemas-and-fieldsets) | Configurable schemas/fieldsets; asynchronous operations for some rewrites | Schema evolution is a managed engineering issue, not inherent corruption |
| 7 | [TeselaGen TEST mapping](https://docs.teselagen.com/en/articles/4508837-test-data-mapping), [platform](https://teselagen.com/platform) | Mapping experimental data and metadata within an integrated biological workflow | Reuse established platform identities where available; benchmark scientist preparation time |
| 8 | [Synthace](https://www.synthace.com/what-we-do), [experimental context](https://www.synthace.com/blog/experimental-context-and-intent) | Experimental design/execution with contextualized structured data | Capturing context at acquisition can be more valuable than reconstructing it afterward |
| 9 | [openBIS](https://openbis.ch/), [ELN types](https://openbis.readthedocs.io/en/7.x/user-documentation/general-users/ELN-types.html) | Configurable research data management and ELN/LIMS object models | Candidate host/adapter for evidence records; no live integration claimed |
| 10 | [FAIRDOM-SEEK](https://docs.seek4science.org/) | Sharing heterogeneous datasets, models, processes, and outcomes | Reuse catalog and study context rather than create another universal catalog |
| 11 | [TetraScience developer overview](https://developers.tetrascience.com/docs/tetra-scientific-data-cloud) | Scientific data transfer, contextualization, and integration architecture | Instrument normalization is established commercial territory; actual adapter coverage must be verified per device |
| 12 | [Siemens Riffyn X](https://blog.siemens.com/2024/10/accelerating-pharma-process-design-and-doe-with-riffyn-x/) | Process/experiment data management and ecosystem integration | Include process context in any real comparison; do not infer absent correction features from a marketing page |
| 13 | [FAIR Data Pipeline](https://www.fairdatapipeline.org/), [issues API](https://www.fairdatapipeline.org/docs/api/java/issues/), [provenance report](https://www.fairdatapipeline.org/docs/data_registry/prov_report/), [paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9376726/) | Versioned data/code provenance, issues, reports, local relational registry and file storage | Closest conceptual prior art; evaluate extending or adapting it before a production rewrite. Official docs warn some material may be outdated |
| 14 | [AiiDA provenance](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/index.html), [consistency](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/provenance/consistency.html) | Provenance graphs and consistency rules for computational workflows | Immutable execution provenance is established; avoid silently mutating old results |
| 15 | [DataJoint](https://docs.datajoint.com/explanation/data-pipelines/) | Relational workflow dependencies coordinated with code and object storage | Strong counterexample to “SQL cannot represent scientific dependency graphs”; candidate production foundation |
| 16 | [DVC](https://doc.dvc.org/user-guide), [pipelines](https://doc.dvc.org/user-guide/pipelines/defining-pipelines) | Git-associated data, parameter, artifact, and pipeline versioning | Reuse for project-level reproducibility where suitable; it does not remove the need to define experimental identities |
| 17 | [lakeFS](https://docs.lakefs.io/guides/version-data/) | Object-data branching, commits, and versioned state | Candidate large-file version control component; not necessary for the small local proof |
| 18 | [Apache Iceberg](https://iceberg.apache.org/docs/latest/evolution/) | Table schema and partition evolution | Consider for analytical scale only after workload measurements; not bundled or tested here |
| 19 | [DuckDB Parquet](https://duckdb.org/docs/current/data/parquet/overview) | SQL analysis of columnar files with projection/filter pushdown | SQL and efficient large analytical storage are compatible; optional analytical backend remains unimplemented |
| 20 | [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html), [recursive queries](https://www.postgresql.org/docs/current/queries-with.html), [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html) | Nested data/indexing, graph traversal, migration options with operation-specific locking/rewrite behavior | Retain SQL as a strong foundation; do not claim all changes are online or all joins are inexpensive |
| 21 | [W3C PROV-O](https://www.w3.org/TR/prov-o/) | Interchange vocabulary for entities, activities, derivation, agents, and revisions | Map concepts instead of inventing a universal provenance ontology; no PROV conformance claimed |
| 22 | [SBOL data model](https://sbolstandard.org/datamodel/), [SBOL3 paper](https://sbolstandard.org/publication/synthetic-biology-open-mclaughlin-2020/) | Machine-readable biological design exchange | Preserve intended designs separately from observed strains; no SBOL parser/conformance claimed |
| 23 | [ISA abstract model](https://isa-specs.readthedocs.io/en/latest/isamodel.html) | Investigation/study/assay context and material/process relationships | Reference for sample-to-data mapping; no full ISA import/export claimed |
| 24 | [Workflow Run RO-Crate](https://www.researchobject.org/workflow-run-crate/profiles/0.5/provenance_run_crate/) | Portable workflow execution provenance | A candidate interchange target; the custom backup here is not an RO-Crate implementation |
| 25 | [MetaboLights](https://www.ebi.ac.uk/training/online/courses/metabolights-quick-tour/study-page/), [data access](https://www.ebi.ac.uk/training/online/courses/metabolights-quick-tour/getting-data-from-metabolights/) | Metabolomics studies with samples, assay metadata, protocols, raw/derived data, and ISA-Tab | Future public-data validation source; this release uses synthetic data, not a MetaboLights study |

## Search coverage and limitations

Searches included the following actual query families, followed by opening
first-party documentation and relevant papers: Experimental Data Depot/ICE
metabolic engineering; TeselaGen/Benchling/Synthace lineage and structured data;
FAIRDOM/openBIS research data management; AiiDA provenance consistency; DataJoint
dependencies; DVC pipelines; lakeFS versioning; Iceberg evolution; DuckDB Parquet;
TetraScience contextualization; Riffyn/Siemens; FAIR Data Pipeline issues and
downstream outputs; SBOL provenance; ISA assay metadata; W3C PROV; MetaboLights.
An additional primary-source search engine was used to check coverage; some
queries returned irrelevant results and were not treated as evidence.

Coverage is by mechanism rather than every commercial ELN/LIMS vendor. There
was no access to paid instances, private roadmaps, customer benchmarks, unpublished
implementations, full patent databases, or a participating laboratory. No vendor
was contacted. No original research data were fetched or analyzed. Public
documentation can establish prior art and interface possibilities, not relative
performance or the completeness of another product's feature set.

## Highest-leverage hypothesis and falsification

Hypothesis: a tightly scoped layer that resolves identities, requires declared
comparison context, freezes calculations, and traces corrections will reduce
time to defensible reuse and prevent consequential silent errors.

Compare three conditions with the same held-out laboratory tasks: (A) current
workflow, (B) the best existing configurable platform available to the lab, and
(C) that platform plus this instrument or equivalent extension. Counterbalance
task order and record setup, ongoing curation, reviewer effort, missed changes,
unnecessary flags, and time to the next experimentally defensible decision.
Include correction cases with no changed conclusion and cases that reverse a
ranking. A faster query alone is not the success endpoint.

Reject the standalone-product hypothesis if an existing platform can configure
the same behavior with comparable correctness and lower total burden. Reject
the scientific-benefit hypothesis if the interface adds curation/alert work
without reducing important errors or decision latency. Do not use synthetic
test pass rates as laboratory efficacy evidence.

## Required components versus separate instruments

One installable instrument can coordinate a registry, byte store, adapters,
computation, dependency analysis, and a scientist interface. Those are distinct
components, not a requirement that a scientist operate several separate apps.
Real deployments must still integrate acquisition instruments and existing
ELN/LIMS platforms. Organizational policy, physical sample labeling, and
scientific interpretation cannot be fully solved in software.
