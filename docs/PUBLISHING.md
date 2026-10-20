# GitHub publication

The repository is https://github.com/forest-savage1234/dbtl-evidence. Claim Review and ME2026 remain independent projects and were not changed by publication.

The original v2.0 gate passed 147 tests, with no failures or skips, at local commit `512d2c26804f61795a17c52330281727a2826848`. The gate receipt is `evidence/v2.0.json`. Source and test modules are unchanged in this publication. Repository URLs and publication documentation were updated; the source/history archive and its original manifest retain their pre-publication bytes.

`history.bundle` contains all original commits and twenty release tags. The publication workflow checks its expected SHA-256, each original tag identity, and every tested v2.0 source hash. It imports exact original Git objects, merges their ancestry into the publication branch while retaining this branch's tree, then atomically pushes the merge and original tags. It does not force-update branches or tags. Concurrent branch changes stop publication rather than overwrite work. The workflow is bounded to this repository and uses its short-lived GitHub Actions token.

The separate research-check workflow tests supported Python versions and both synthetic demonstrations. Remote CI results must be read from Actions; local passing tests alone are not proof of remote CI success. A failed history import does not erase the source/history archive. The bundled history can always be recovered with `git clone history.bundle reconstructed-history`.

The HTML assessment under `release-artifacts/v2.0/` was generated before publication; its earlier repository-availability statement is historical. Scientific and industrial validation limits remain open as documented in V2_VALIDATION.md.
