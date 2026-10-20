# Publish the independent repository

The local history is complete through v2.0. A GitHub lookup for `forest-savage1234/dbtl-evidence` returned 404 on 20 October 2026. The connected GitHub capability can edit existing repositories but cannot create one, and no authenticated GitHub CLI is installed here. The unavailable repository is not evidence that a similarly named private repository does not exist elsewhere. No upload is claimed.

Create or make accessible the intended standalone repository before publishing. Do not put this code into Claim Review or ME2026. Prefer a private repository until visibility and licensing are chosen. With an authenticated GitHub CLI on a machine you control, the complete-history route is:

```bash
git clone history.bundle dbtl-evidence
cd dbtl-evidence
gh repo create forest-savage1234/dbtl-evidence --private --source=. --remote=origin --push
git push origin --tags
```

If the repository already exists, inspect its history and access first. Do not force-push, replace existing branches or assume an empty repository. Configure the remote and push only after reconciling any existing work. A future publication should update citation metadata with the actual repository URL, choose a license, and record the resulting remote commit/release identities. CI is configured but no remote Actions result is claimed.
