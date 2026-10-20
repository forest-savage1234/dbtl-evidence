> Historical baseline audit at the recorded v1.0 preparation commit. The 69-test count and "not modified" statements describe that audit. For the subsequent implemented v1.1–v2.0 series and remaining acceptance gates, see [V2_VALIDATION.md](V2_VALIDATION.md). This baseline is preserved, not silently reinterpreted as a current-feature audit.

# Decision integrity for metabolic engineering

Literature audit and engineering campaign · 20 October 2026
Projects: **Claim Review** and **DBTL Evidence**
Status: **research campaign; industrial benefit unproven**

## The decision to engineer for

The highest-leverage hypothesis is a system that helps a scientist answer: **Which strain should advance, under which process conditions, and does that decision still hold when available evidence changes?** That is more testable than replacing SQL or unifying all biological data.

Keep the projects separate. Claim Review should establish what can be reconstructed about a published numerical claim. DBTL Evidence should establish what a local experimental decision depended on, which comparisons its policy permits, and what needs reassessment as evidence changes. A versioned interchange contract connects them. Importing a supported calculation must never turn it into a verified experimental result.

Neither instrument, individually or together, completely establishes biological truth, physical sample identity, assay validity, or industrial transferability from software records alone. A single interface can coordinate several components and existing laboratory instruments. Additional newly invented database products are not inherently necessary. Independent measurements, domain judgment, and organizational ownership remain necessary.

**Invest first in decision semantics and reassessment over an evolving evidence pool.** Revisions to cited data are only one trigger. Newly eligible results, contradictory observations, changed eligibility rules, withdrawn evidence, and uncertain evidence coverage can also require review. This is the same decision-reassessment problem at realistic scale.

That priority is an engineering inference from the literature and audit, not a demonstrated ranking of industry-wide financial losses. No market size, savings, novelty, or superiority claim is established.

## What was actually investigated

The evidence ledger contains **18 scientific sources**. Targeted full-text sections were inspected for 10, including one correction notice; eight support only the recorded indexed abstracts or primary-text extracts. It includes experiments, analytical methods, modeling, software methods, and a perspective. This is a targeted review, not a preregistered systematic review or an exhaustive census.

Searches covered industrial scale and scale-down, genetic instability, metabolite measurement, uncertainty, literature-derived metrics, automated DBTL, interoperability, and provenance prior art. Two search engines and legitimate institutional article copies were used. Irrelevant results were discarded. Access limits are retained. No private industrial dataset or licensed platform was available.

Actual implementations were inspected:

- Claim Review browser **0.3.2**, file commit **45b8559fc6ec5460cd7a11dffc411d22aec52115**; Git blob **dc3cf7bb283d2e6eac5043be81325e5d231dd568**.
- DBTL Evidence at **b99188386e8b0c60133b09f072b23cd57154b2be**, following the narrow reference v1.0.
- **11 executable synthetic boundary probes**, including positive controls. They document current limits; they do not fix them.
- The existing DBTL suite passed **69 tests**. These are software-behavior checks, not laboratory efficacy evidence.

No original experimental dataset was independently reproduced here. The four existing ME2026 forensic cases were not re-adjudicated. A missing public file is not evidence that a biological result is false.

## Literature findings that change the priorities

| Industrial problem | Evidence and boundary | Engineering consequence |
| --- | --- | --- |
| Performance depends on the operating regime | An industrial-strain study found different most-effective acetate-reduction strategies under unrestricted growth versus carbon-limited glucose shock [S01]. | Scope comparisons to a declared target process. |
| Cells experience histories | Combined substrate/oxygen oscillations differed from isolated oscillations in a model-guided scale-down study [S02]. Measured large-scale comparisons also exist [S18]. | Represent trajectories, sampling alignment, stress history and observed-versus-modeled roles. |
| Production material changes | A fermentation-timescale simulation linked production decline to changing population genetics [S03]. | Genotype observations need material, time/generation, assay, coverage and population scope. |
| Precision differs from certainty | A Pichia interlaboratory study reported substantial uncertainties, with most results agreeing within them [S04]. Sampling and extraction can also affect quality [S05]. | Separate arithmetic precision, repeatability, uncertainty and assay validity. |
| A proxy differs from its target | A flaviolin campaign improved an optical proxy by 148% and direct HPLC titer by 70%; authors explicitly validated both [S10]. | Preserve assay identity and validation links. |
| Literature metrics require interpretation | A literature-curated modeling study described reporting differences, undefined media and curation burden [S08]. | Require denominator, time, volume, substrate and missingness semantics. |
| Organized data do not guarantee useful predictions | ART documents probabilistic recommendations and both successful and difficult examples [S06]. Construction and expression constraints also mattered [S07]. | Evaluate prospective decision utility and controllability separately from model fit. |
| Integration has substantial prior art | teemi connects design, observed genotype, production and learning [S09]; ICE/EDD/ART integration is demonstrated [S15]. | Reuse adapters and prove incremental benefit against a configured existing workflow. |
| Correction propagation is established | FAIR Data Pipeline links data/code issues to downstream outputs [S14]. | A possible contribution is the domain workflow and measured burden reduction. |
| Corrections vary in consequence | The flaviolin correction repairs an author's surname [S11]. | Preserve history without automatically rejecting quantitative conclusions. |

The recent isoprenol automation study [S12] and bacterial isotope-ratio assay [S13] reinforce the need to examine acquisition and validation. Access limits prevent detailed implementation claims here. The interoperability paper is a perspective [S16], not empirical evidence that standardization removes integration cost. A 2026 scale-up analysis reuses historical curves [S17]; reused data must retain their original experimental identity.

These studies establish mechanisms and examples. They do not establish their frequency or economic impact across all industrial laboratories.

## Where Claim Review falls short

The current core reads retained XLSX/CSV/TSV observations, reconstructs selected arithmetic and summary statistics, checks supported dimensions, and compares declared conditions. Its result remains PARTIAL_SUPPORT and explicitly leaves measurement, context, and independence questions open.

| Boundary | Current behavior | Missing capability |
| --- | --- | --- |
| Quantity meaning | Units and operation are checked. | Product/biomass and product/substrate can both be g/g. Dimensions cannot choose the scientific estimand. |
| Aggregation | Replicated inputs are combined as group means, with an explicit warning. | Source-bound pairing, weighting, repeated measures, hierarchical designs and missing-pair policies. |
| Independent replication | Counts and distinct declared IDs can be checked; independence is NOT_ESTABLISHED. | Aliquot/culture hierarchy, shared controls and duplicate-experiment resolution. |
| Analytical validity | Measurement-history gaps remain open. | Raw integration, chemical identification, standards, fitting, matrix effects, recovery and drift assessment. |
| Condition completeness | Selected bindings are checked against cells. | Correct selected fields do not establish that every relevant field was selected. |
| Publication evolution | Hashes and publication notes are retained. | Linked revisions, withdrawal monitoring and consequence-aware review. |
| Cross-paper reuse | Claims can be replayed and exported. | Demonstrated ontology mapping, comparability and industrial eligibility. |
| Workflow value | Browser-based checking is available. | Controlled evidence of faster defensible review or fewer consequential errors. |

The pinned [review core](https://github.com/forest-savage1234/casefile-provenance-demo/blob/45b8559fc6ec5460cd7a11dffc411d22aec52115/claim-review/index.html) defines calculate, statistics, conditionCheck, summaryCheck and review. Snapshot lines 4193–4194 implement dimensions; 4269 implements statistics; 4284–4300 define the assessment and its limitations.

The next Claim Review feature should be an **explicit scientific estimand**, followed by source-bound estimator choice and separate machine-readable evidence assessments. Supported arithmetic remains useful while the experiment remains unresolved.

## Where DBTL Evidence falls short

The reference instrument retains typed dependencies and exact versions, stores source bytes outside SQL, freezes descriptive titer datasets, replays history, and identifies superseded dependencies. Those are useful foundations.

| Boundary | Current behavior | Missing capability |
| --- | --- | --- |
| Changing available evidence | Findings follow revisions inside existing dependency closures. | Newly eligible measurements outside a frozen cohort create no finding. |
| Genotype | asserted_verified requires an artifact and is explicitly an operator assertion. | Content assessment, observation time, coverage, clone/population and assay scope. |
| Biological n | Technical acquisitions are averaged within culture entities; culture means receive equal weight. | Aliased entities can inflate biological_n; experimental-unit identity remains curator-dependent. |
| Process context | Ten policy fields must match. | Realized trajectories and extensions are outside the policy; exact matching can also prevent useful stratified comparisons. |
| Measurement | One linear peak-area model calculates titer. | Fit, covariance, matrix/recovery, drift and chromatogram assessment; QC is supplied as an assertion. |
| Industrial objective | Titer, sample SD, minimum culture count and descriptive rank. | Yield, productivity, stability, recovery and economic tradeoffs. |
| ML | A model can be a versioned dependent object. | Full training provenance, leakage control, domain-shift evaluation and prospective utility. |
| Operations | Local transactions, consistency checks and backup/restore. | Authenticated actors, multi-organization permissions, external attestation and industrial workload validation. |

These limits appear in domain.py, calc.py, graph.py and review.py. In particular, refresh_cohort advances existing members; it does not discover new independent results. The provenance graph represents derivation, not metabolic causality.

The next DBTL feature should be **evidence-pool membership-change reassessment**, accompanied by honest genotype and experimental-unit status. A database-engine migration does not resolve these issues.

## Executable challenges

Every fixture is synthetic. Expected observations were defined before execution. Passing a boundary probe does not mean its limitation is repaired.

| Probe | Challenge | Observed result | Meaning |
| --- | --- | --- | --- |
| CR-01 | Product/biomass with mass units | 0.50 g/g; SOURCE_REPLAY; PARTIAL_SUPPORT | Correct arithmetic; substrate-yield meaning unestablished. |
| CR-02 | Numerators 1,9; denominators 1,3 | Ratio of means 2.50, with warning | Mean of paired ratios is 2.00. |
| CR-03 | Three labels from one declared physical origin | n=3; independence NOT_ESTABLISHED | Observation count is not independent culture count. |
| CR-04 | Wrong expected hash | WITHHELD | Changed bytes are not silently accepted. |
| CR-05 | Mass to concentration without volume | WITHHELD | Incompatible dimensions are rejected. |
| DE-01 | Assertion note as genotype evidence | asserted_verified accepted; included | Attachment content is not verified. |
| DE-02 | Different trajectory extensions; same nominal context | Both included | Retained extensions are not comparison rules. |
| DE-03 | New eligible high-titer strain outside cohort | Review queue remains 0 | Membership growth is outside current tracking. |
| DE-04 | Two IDs declaring one physical culture | biological_n=2; rank assigned | IDs do not establish independent cultures. |
| DE-05 | Different declared batch | Explicit exclusion | Supported context policy works. |
| DE-06 | Revised existing calibration | Current comparison blocked | Existing correction propagation works. |

DE-01 and DE-02 are documented scope limits, not hidden claims of genotype or trajectory verification. CR-02 and CR-03 already disclose their limitations in exports. DE-03 becomes consequential if the product is described as maintaining decisions against newly available evidence. That claim must wait for a bounded pool/watch implementation and evaluation.

## Separate instruments, explicit handoff

| Component | Owns | Must not inherit automatically |
| --- | --- | --- |
| Claim Review | Publication/source identity, cell bindings, declared calculation, open questions | Local sample identity, assay validity, independent replication, industrial relevance |
| Shared draft contract | Versioned identities, hashes, locations, estimand, separate assessments, declared mappings and scope | Universal verified status or scientific endorsement |
| DBTL Evidence | Local material/process records, comparison policy, pool snapshots, decisions and reassessment | Treating published evidence as a local measured sample |
| Existing ELN/LIMS, assays and recommendation tools | Acquisition, execution, validated analytical pipelines and experimental recommendations | Trust merely because a tool is integrated or FAIR |

The contract is a **specification draft**, not an implemented importer or a third independent product. Both projects must remain runnable alone. A literature claim can inform a local decision with an explicit justification while retaining its original limitations.

Reuse established provenance, investigation/assay and biological-design vocabularies. Similar field names do not establish SBOL, ISA, PROV or RO-Crate conformance. Pin standards and demonstrate round-trip behavior before claiming conformance.

## Campaign gates

Order work by risk of an unsupported consequential assertion, then by the burden of defensible work. Priorities are judgments to test, not fabricated ROI scores.

| Gate | Concrete work | Adverse challenge | Advance only when |
| --- | --- | --- | --- |
| G0: decision/corpus | C00. Define one advancement decision; screen at least 12 varied public cases as a coverage pilot. | Reviewers disagree; files are inaccessible; plausible arithmetic lacks scientific context. | Every case has source/version/access records, explicit unresolved labels and an adjudication path. |
| G1: meaning | C01–C03, C06–C07. Estimands, pairing, genotype observations, experimental units, separate assessments. | Wrong denominator, renamed aliquot, insufficient genotype artifact. | Independent oracles and domain review agree; missing evidence stays open across exports. |
| G2: evolving evidence | C04–C05, C11–C12. Pool/predicate versions, handoff and consequence-aware review. | New result, withdrawal, changed policy, interrupted ingestion, harmless correction. | Correct decisions reopen; history remains replayable; harmless changes do not become scientific rejection. |
| G3: assay/process | C08–C10. Validate one assay path, trajectories, covariance and transfer scope. | Proxy mismatch, matrix bias, drift, shared uncertainty, censoring and time misalignment. | Scope has assay-specific evidence, independent numerical validation and explicit limits. |
| G4: baselines | C13–C15. Blinded tasks, reliability and optional ML export. | An existing extension does the same with less work; blanket flagging looks safe. | Errors, useful coverage and total work are measured with uncertainty on held-out tasks. |
| G5: external validation | C16–C17. A laboratory validates acquisition-to-decision behavior. | Real materials, files, identities, workload and new-evidence challenges. | Independent external evidence supports each release claim. |

The backlog contains **18 proposed work packages**, each with project ownership, dependencies, acceptance and stop criteria, and source/probe links. Owners are roles, not invented collaborators. No external issues were created.

Use small increments. Each must name the added claim, the evidence needed, adverse cases, and behavior to withhold. A version number is not validation. Existing v1.0 denotes the narrow reference implementation; it must not become an industrial maturity claim.

## Evolving-evidence design

A frozen cohort answers what supported a past decision. A watched pool answers whether relevant evidence available within a declared system changed. Both are needed.

The pool contract needs source boundaries, analyte/quantity/assay scope, a selection predicate, unknown-metadata policy, registered versions, access status and transactional event watermark. Preserve exclusions and uncertain candidates. A registry watermark means complete processing of that bounded event history, not completeness of world literature or undisclosed laboratory data.

On change, compute membership and eligibility deltas against the preceding snapshot. Capture the event sequence and predicate/code versions. Identify affected decisions/models and create an explanatory review item. Preserve old evidence and results. A new observation does not automatically disprove an earlier conclusion; recalculation does not authorize a new decision.

Use distinct states: historically replayable, current for a named pool snapshot, reassessment pending, and pool coverage unknown. A process that missed events must not claim current coverage merely because its graph is internally consistent.

Challenge additions, duplicates, revised identifiers, changed predicates, withdrawals, restored access, idempotent replay, concurrency and interrupted ingestion. Unknown matches must not disappear as exclusions. Permission-sensitive events require deployment-specific design and are not implemented in the local prototype.

## Measurement and statistical integrity

Declare the measurand first: proxy/product, compartment, mass/carbon basis, substrate charged/consumed, initial/final/time-varying volume and time interval. Concentration divided by total hours is a declared endpoint-average quantity, not automatically an instantaneous rate. Missing denominators prevent the corresponding claim while observations remain retained.

The linear model is y = d(r − b)/a, where r is response, b intercept, a slope and d dilution, with a known unit-conversion factor. Replay does not include measurement uncertainty.

An uncertainty model must separate replicate variability, calibration covariance, standards, dilution/volume, matrix bias and assay-specific components. Shared calibrations correlate errors across samples. For a difference, variance is Var(A) + Var(B) − 2 Cov(A,B). Treating all errors as independent can overstate or understate uncertainty.

When bias or covariance is unidentified, preserve the gap and justified sensitivity scenarios. Do not invent distributions, substitute SEM for total measurement uncertainty, or use interval overlap as an automatic decision rule. An implementation needs an independent analytic/simulation oracle and declared model scope.

Define biological replication through the experimental design. Aliquots and reacquisitions stay linked. Shared inoculum, stocks and controls require design-aware assessment; they do not automatically make independently treated cultures identical. Keep n observed, declared units, assessed independence, blocking and exclusions separate.

Retain censored and out-of-range observations. Excluding them from one calculation can itself introduce selection bias. Examine consequences under declared models; silently substituting zero is unacceptable.

## Evaluation that could falsify the product hypothesis

Compare three conditions on matched tasks: current laboratory workflow; the best accessible configured existing platform; and that platform with this layer or an equivalent extension. Count setup, adapters, curation, failed imports, review, maintenance and alert handling. Query speed is insufficient.

Randomize/counterbalance order. Group repeated tasks by original experiment family. Separate development and held-out evaluation. Independent reviewers specify supportable and appropriately unresolved answers before evaluation; software cannot adjudicate biological ambiguity.

Measure:

- Serious unsupported assertions, including false scientific support after correct arithmetic.
- Missed consequential source or pool changes.
- Unnecessary alerts, including harmless corrections.
- Useful coverage among adjudicable tasks.
- Appropriate withholding versus blanket refusal.
- Total human time per correctly resolved task.
- Reproducibility and recovery after failures.
- If evaluating ML: grouped/temporal holdouts, train-only transforms, calibration, domain shift and prospective decision utility.

Targets must be chosen before the held-out evaluation. One proposed business target is **20% less total time per correctly resolved task**, with no worse serious-error or useful-coverage rates. This is a proposed target, not an observed or literature-derived benefit. Pilot measurements determine feasibility, variance, power and meaningful improvement; then freeze the final protocol.

Zero observed failures is not zero risk. Under independent, representative binomial sampling, zero failures in n trials has a one-sided 95% upper bound of 1 − 0.05^(1/n): approximately 1% at n=300 and 22% at n=12. Seeded variants of one paper are not independent industrial trials. A small fixture suite cannot establish a low real-world error rate.

Redirect to an adapter, configuration or upstream contribution if an existing platform gives equivalent correctness with less burden. Stop efficacy claims if useful coverage collapses, difficult cases are selectively dropped, or setup/curation erase the advantage.

## Existing solutions and unresolved comparisons

| Family | Reuse | What to test |
| --- | --- | --- |
| ICE / EDD / ART | Construct identities, experimental exchange, recommendations [S06, S15] | Revisions, membership-change review, status preservation and effort in the configured workflow |
| teemi | Literate execution and design/measurement linkage [S09] | Reassessment and mapping/control maintenance burden |
| FAIR Data Pipeline / provenance systems | Dependency and issue propagation [S14] | Domain assay/estimand semantics and evolving membership |
| Commercial ELN/LIMS and data platforms | Existing acquisition, identities, access and context | Same frozen tasks including setup cost; undocumented features remain unknown |
| SQL / graph / analytical storage | Appropriate transactional, traversal and analytical components | Measured workload, consistency and maintenance; no engine establishes scientific validity |

RESEARCH.md retains the broader 25-system map. This campaign challenges the scientific and operational claims. No paid platform was tested hands-on. SQL supports relational graph patterns and nested data; separate object storage is a normal architecture. Migration needs a measured workload and demonstrated architectural constraint.

## The next ten work sessions

This is an ordering proposal, not a staffing/calendar promise. Domain-review availability governs scientific gates.

| Sessions | Work | Reviewable output |
| --- | --- | --- |
| 1–2 | Build C00 rubric; screen public cases with access tiers. | Pilot manifest, unresolved questions, target decision |
| 3–4 | Review C01/C02 contract and quantity semantics. | Denominator/proxy fixtures; no status strengthening |
| 5–6 | Implement one bounded pool predicate and membership delta path. | New-result/withdrawal tests, watermark and history checks |
| 7–8 | Add source-bound estimator choice and experimental-unit declarations in Claim Review. | Independent oracle, pairing and alias fixtures |
| 9–10 | Run a baseline task pilot including all curator time. | Pilot results; build/reuse decision; held-out evaluation plan |

Without scientific adjudication, continue software fixtures while leaving scientific validation open. Do not assume private data or wet-lab access. Assay, process-transfer and industrial gates cannot be closed by desktop work alone.

## Delivered now and remaining work

Completed: source ledger, exact-version audit, eleven probe results, eighteen-package backlog, draft interchange schema/contract, this report, and unchanged production reference code with retained history.

Remaining: validated benchmark corpus, scientific upgrades, working importer, analytical validation, user trial, industrial deployment and measured benefit. These are gates, not implied achievements.

Claim Review production files and DBTL production modules were not modified. Research documents and probe tools are added to the DBTL repository. The archive is ready for review and repository publication; no GitHub upload is claimed.

## Source ledger

Access labels distinguish inspected full-text sections from indexed abstracts/extracts. Queries and limitations are in evidence/campaign/sources.json. Facts and engineering inferences are separate. No article text or raw experimental dataset is bundled.

### S01 · 2024

[Minimizing acetate formation from overflow metabolism in Escherichia coli: comparison of genetic engineering strategies to improve robustness toward sugar gradients in large-scale fermentation processes](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2024.1339054/full)

**Access:** full text sections. **Type:** industrial-strain experiments. **DOI:** 10.3389/fbioe.2024.1339054.

**Observed:** The most effective acetate-reduction strategy differed between unrestricted growth and carbon-limited glucose-shock conditions.

**Limit:** An industrial strain and industrial motivation; the reported experiments are microplate and small-bioreactor tests, not a validated universal scale-transfer rule.

**Engineering inference:** Represent process regime and target environment in comparison eligibility.

### S02 · 2024

[Combined oxygen and glucose oscillations distinctly change the transcriptional and physiological state of Escherichia coli](https://enviromicro-journals.onlinelibrary.wiley.com/doi/10.1111/1751-7915.70051)

**Access:** full text sections. **Type:** model-guided scale-down experiments. **DOI:** 10.1111/1751-7915.70051.

**Observed:** Combined glucose/oxygen oscillations produced responses distinct from the isolated oscillations; some transcriptional responses persisted.

**Limit:** The 90 m³ environment is modeled; actual measurements are from scale-down experiments.

**Engineering inference:** Store realized trajectories, temporal alignment, stress history, and model-versus-observation roles.

### S03 · 2018

[Diverse genetic error modes constrain large-scale bio-based production](https://www.nature.com/articles/s41467-018-03232-w)

**Access:** full text sections. **Type:** experimental fermentation-timescale simulation and sequencing. **DOI:** 10.1038/s41467-018-03232-w.

**Observed:** Production loss was associated with changing population genetics in engineered E. coli despite plasmid selection.

**Limit:** Serial-passage simulation and a simplified population model; not a survey establishing industrial prevalence.

**Engineering inference:** Separate intended design from observed population state and attach verification to time, material, method, and coverage.

### S04 · 2013

[Interlaboratory comparison for quantitative primary metabolite profiling in Pichia pastoris](https://pubmed.ncbi.nlm.nih.gov/23604417/)

**Access:** indexed abstract. **Type:** two-laboratory analytical comparison. **DOI:** 10.1007/s00216-013-6964-4.

**Observed:** Reported expanded combined uncertainties (K=2) were 21–48% and 30–57%; most concentrations agreed within uncertainty.

**Limit:** Specific intracellular metabolites and methods; these ranges are not a universal error model for product titer.

**Engineering inference:** Represent metrological uncertainty separately from arithmetic precision and replicate variation.

### S05 · 2023

[Optimized Fast Filtration-Based Sampling and Extraction Enables Precise and Absolute Quantification of the Escherichia coli Central Carbon Metabolome](https://www.mdpi.com/2218-1989/13/2/150)

**Access:** indexed primary text extracts. **Type:** sampling and analytical method development. **DOI:** 10.3390/metabo13020150.

**Observed:** Sampling, extraction, leakage, and residual salts affected measurement quality.

**Limit:** Full-text retrieval was blocked; conclusions here are restricted to indexed author text, not a reanalysis of the method.

**Engineering inference:** Track sample handling and matrix evidence; an extraction-protocol identifier alone does not validate a measurement.

### S06 · 2020

[A machine learning Automated Recommendation Tool for synthetic biology](https://www.nature.com/articles/s41467-020-18008-4)

**Access:** full text sections. **Type:** method, simulations, retrospective examples and experimental demonstration. **DOI:** 10.1038/s41467-020-18008-4.

**Observed:** ART provides probabilistic recommendations and documents both successful examples and weak prediction in the dodecanol case.

**Limit:** Data requirements depended on the problem; prediction accuracy and successful experimental recommendation were not equivalent endpoints.

**Engineering inference:** Reuse recommendation engines and test prospective decision utility independently of model fit.

### S07 · 2019

[Lessons from Two Design–Build–Test–Learn Cycles of Dodecanol Production in Escherichia coli Aided by Machine Learning](https://pubs.acs.org/doi/full/10.1021/acssynbio.9b00020)

**Access:** indexed primary text extracts. **Type:** two experimental DBTL cycles. **DOI:** 10.1021/acssynbio.9b00020.

**Observed:** Authors identified expression-control limitations, build effects, training-data limitations, and the need to check production-strain plasmids.

**Limit:** Publisher full text was inaccessible during this review; detailed independent interpretation also uses S06, which explicitly reexamines this case.

**Engineering inference:** Record failed builds, intended-versus-observed constructs, and actuator uncertainty.

### S08 · 2019

[Machine learning framework for assessment of microbial factory performance](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0210558)

**Access:** full text sections. **Type:** literature-curated microbial-production dataset and modeling. **DOI:** 10.1371/journal.pone.0210558.

**Observed:** Authors described burdens of manual curation, nonstandard metrics, undefined media, and omitted stability/byproduct context.

**Limit:** A literature-derived modeling study; its observations do not establish the present-day prevalence or cost of every bottleneck.

**Engineering inference:** Capture denominator semantics, curation decisions, missingness, and experimental grouping before ML export.

### S09 · 2024

[teemi: An open-source literate programming approach for iterative design-build-test-learn cycles in bioengineering](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011929)

**Access:** full text sections. **Type:** software method with a yeast engineering testbed. **DOI:** 10.1371/journal.pcbi.1011929.

**Observed:** Literate workflows connected design, observed genotypes, production measurements, and iterative learning; plate reference measurements were used for normalization.

**Limit:** A specific experimental demonstration, not a controlled comparison proving universal error reduction or novice usability.

**Engineering inference:** Benchmark against workflow reuse; version normalization controls and include curator workload.

### S10 · 2025

[Machine learning-led semi-automated medium optimization reveals salt as key for flaviolin production in Pseudomonas putida](https://www.nature.com/articles/s42003-025-08039-2)

**Access:** full text sections. **Type:** semi-automated active-learning campaigns. **DOI:** 10.1038/s42003-025-08039-2.

**Observed:** Campaign 1 improved an optical proxy by 148% and directly measured HPLC titer by 70%; authors explicitly distinguished and validated these endpoints.

**Limit:** One host/product setting; method and metric transfer need validation.

**Engineering inference:** Preserve proxy-versus-direct assay identity and link validation evidence rather than equate endpoints.

### S11 · 2025

[Author Correction: Machine learning-led semi-automated medium optimization reveals salt as key for flaviolin production in Pseudomonas putida](https://www.nature.com/articles/s42003-025-08141-5)

**Access:** full text sections. **Type:** publication correction. **DOI:** 10.1038/s42003-025-08141-5.

**Observed:** The correction repairs an author's misspelled surname.

**Limit:** This notice does not report a numerical correction.

**Engineering inference:** Classify correction scope; do not invalidate quantitative conclusions merely because a correction exists.

### S12 · 2025

[Automation and machine learning drive rapid optimization of isoprenol production in Pseudomonas putida](https://www.nature.com/articles/s41467-025-66304-8)

**Access:** indexed abstract and primary extracts. **Type:** automated experimental DBTL study. **DOI:** 10.1038/s41467-025-66304-8.

**Observed:** The study combines automation, multiplexed perturbations, validation, and ML to improve isoprenol production.

**Limit:** PDF metadata was retrievable, but later body requests failed. No detailed effect-size or QC-algorithm claim is used here.

**Engineering inference:** Compare with validated acquisition-to-learning workflows rather than assume storage is the only constraint.

### S13 · 2026

[A Robust Isotope Ratio LC–MS/MS Workflow for High-Throughput Metabolic Profiling of Bacteria](https://pubs.acs.org/ancham/article/98/33/23989/5250716/A-Robust-Isotope-Ratio-LC-MS-MS-Workflow-for-High)

**Access:** indexed primary text extracts. **Type:** analytical method development. **DOI:** 10.1021/acs.analchem.5c04931.

**Observed:** A recent study reports an isotope-ratio workflow for bacterial intracellular metabolite profiling.

**Limit:** Full-text retrieval remained blocked; final article DOI was confirmed in the primary indexed record. No independent assay reanalysis was performed.

**Engineering inference:** Evaluate established quantitative assays; software replay should consume their evidence without claiming to replace them.

### S14 · 2022

[FAIR data pipeline: provenance-driven data management for traceable scientific workflows](https://doi.org/10.1098/rsta.2021.0300)

**Access:** full text sections. **Type:** scientific software architecture and worked examples. **DOI:** 10.1098/rsta.2021.0300.

**Observed:** The pipeline tracks data/code provenance and propagates issues to affected downstream outputs.

**Limit:** Developed for epidemiological workflows; not an industrial metabolic-engineering performance trial.

**Engineering inference:** Correction-sensitive provenance is established prior art; compare an extension before building a production replacement.

### S15 · 2021

[Multiomics Data Collection, Visualization, and Utilization for Guiding Metabolic Engineering](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2021.612893/full)

**Access:** full text sections. **Type:** integrated computational methods demonstration. **DOI:** 10.3389/fbioe.2021.612893.

**Observed:** ICE, EDD and ART form an integrated workflow; multiomics data in part of the demonstration are generated computationally.

**Limit:** The paper explicitly labels simulated omics and assumptions; it is not evidence that all displayed multiomics are real instrument measurements.

**Engineering inference:** Reuse integration patterns and label simulation, observed evidence, and inference distinctly.

### S16 · 2025

[Abstraction hierarchy to define biofoundry workflows and operations for interoperable synthetic biology research and applications](https://www.nature.com/articles/s41467-025-61263-6)

**Access:** indexed primary text extracts. **Type:** perspective / proposed framework. **DOI:** 10.1038/s41467-025-61263-6.

**Observed:** The authors propose a hierarchy for biofoundry workflow interoperability.

**Limit:** A perspective is not an empirical demonstration that standards eliminate integration cost.

**Engineering inference:** Use workflow/process vocabularies as integration candidates; require round-trip tests.

### S17 · 2026

[Data-efficient hybrid parameter scaling for accurate microbial bioreactor scale-up](https://pubmed.ncbi.nlm.nih.gov/41848891/)

**Access:** indexed abstract. **Type:** modeling using historical fermentation curves.

**Observed:** The analysis reuses lipase time courses from Geraats (1994) across several scales.

**Limit:** Historical curve reuse is not new prospective industrial validation; final DOI and full methods were not recovered.

**Engineering inference:** Track original experiment identity and held-out scales to avoid counting reused evidence as new replication.

### S18 · 2001

[Physiological responses to mixing in large scale bioreactors](https://pubmed.ncbi.nlm.nih.gov/11165362/)

**Access:** indexed abstract. **Type:** 22 m³ / laboratory / scale-down fermentation comparison. **DOI:** 10.1016/S0168-1656(00)00365-5.

**Observed:** E. coli fed-batch cultivations at 22 m³ were compared with laboratory and scale-down processes.

**Limit:** An older, specific process comparison; no generalized prevalence or present-day cost estimate is inferred.

**Engineering inference:** Anchor scale-transfer challenges in measured large-scale experiments as well as modern simulations.


## Reproduction

Run **python3 tools/campaign_probe.py** from the repository root. Run **node tools/claim_scope_probe.cjs /absolute/path/to/index.html** using the pinned public Claim Review snapshot. That script checks the exact Git blob and executes the extracted calculation core without modifying the app.

The Claim Review HTML and dependencies are not duplicated into DBTL. Obtain the pinned file through GitHub and preserve its bytes. The retained result includes Git blob and SHA-256 fingerprints.

Outputs: evidence/campaign/dbtl-probes.json and evidence/campaign/claim-probes.json. DBTL production modules are fingerprinted. All probe data are synthetic and local. A source-package manifest covers the deliverable files. Tests do not authenticate laboratory materials or certify scientific conclusions.
