# Contributing & release process

How code moves from a laptop to production. The merge rules below are **enforced by
GitHub** (rulesets in `.github/rulesets/`, free on public repos). There is **no
GitHub Actions / paid CI**: checks run on your machine and deploys are one command.

## Branches

| Branch | Purpose | Deployed to | Direct push |
|---|---|---|---|
| `main` | Production. Every commit is releasable. | production | ❌ PR only |
| `dev` | Integration. Features land here first. | staging | ❌ PR only |
| `feat/*`, `fix/*`, `chore/*` | One change each, branched from `dev` | — | ✅ |
| `hotfix/*` | Urgent production fix, branched from `main` | — | ✅ |

`dev` is the default branch, so new PRs target it automatically. Neither `main` nor
`dev` can be force-pushed or deleted.

## Everyday flow

```bash
git switch dev && git pull
git switch -c feat/calendar-drag        # or fix/…, chore/…
# …work, commit…
# before pushing: run the checks (see "Checks before a PR")
git push -u origin feat/calendar-drag
gh pr create --base dev --fill          # or open the PR on github.com
```

1. Fill in the PR checklist. All review conversations must be resolved before merging.
2. **Squash-merge** into `dev` (one clean commit per feature). The branch is auto-deleted.
3. Deploy to staging: `bash scripts/deploy.sh staging`.

## Releasing to production

1. In a PR into `dev`, bump `__version__` in `sprint/__init__.py` (e.g. `0.2.0`).
2. Open a PR **`dev` → `main`**:
   ```bash
   gh pr create --base main --head dev --title "Release v0.2.0"
   ```
   It needs **1 approving review** from a code owner. Working solo, an admin can
   skip the approval, but only through a PR (`gh pr merge --merge --admin`). Nobody
   can push to `main` directly.
3. Merge with a **merge commit**, never squash, so `dev` and `main` keep a shared history
   and the next release doesn't conflict.
4. Tag the release (tags are the rollback points; release tags can't be moved or deleted):
   ```bash
   git switch main && git pull
   git tag -a v0.2.0 -m "v0.2.0" && git push origin v0.2.0
   gh release create v0.2.0 --verify-tag --generate-notes     # optional release page
   ```
5. Deploy: `bash scripts/deploy.sh production`.

## Hotfixes

```bash
git switch main && git pull && git switch -c hotfix/login-loop
# fix, push, PR → main (same approval rule as a release), merge commit
```
Afterwards, open a PR **`main` → `dev`** (merge commit) so the fix isn't lost on the
next release.

## Checks before a PR

There's no CI server, so the author runs these in their bench/devcontainer:

```bash
pre-commit run --all-files                    # ruff, eslint, prettier (once: pre-commit install)
bench --site development.localhost run-tests --module sprint.tests.test_api
bench --site development.localhost run-tests --module sprint.tests.test_automation
```
If you touched `frontend/src`, rebuild (inside the devcontainer) and commit
`sprint/public/frontend` + `sprint/www/sprint.html` in the same PR. Servers never
run `yarn build`; they use the committed assets.

## Deploying

`scripts/deploy.sh` runs from your machine (Git Bash on Windows works) and drives the
server over SSH:

```bash
bash scripts/deploy.sh staging              # deploys origin/dev
bash scripts/deploy.sh production           # deploys origin/main
bash scripts/deploy.sh production v0.1.0    # rollback to a tag
```

It refuses code that isn't pushed, refuses production code that isn't on `main`, and
asks you to type the environment name to confirm. On the server
(`scripts/remote-deploy.sh`) it runs: backup (DB + files) → maintenance mode on →
checkout the exact commit → `bench setup requirements` → `bench migrate` (runs the
`ensure_*` hooks) → `bench build --app sprint` → `bench restart` → maintenance off →
HTTP health check (`/api/method/ping`). If any step fails, the code goes back to the
previous commit automatically. Database migrations aren't reversed; use the
pre-deploy backup in `sites/<site>/private/backups` if needed.

### One-time server setup
1. Set up a production bench on the server (`bench setup production <user>`, see
   `DEPLOYMENT.md`) with `apps/sprint` cloned from this repo. The repo is public, so a
   plain https clone works.
2. Make sure you can `ssh <user>@<server>` with a key.
3. Create `.deploy/production.env` (and `.deploy/staging.env`) locally. The folder is
   git-ignored:
   ```bash
   SSH_HOST=203.0.113.10
   SSH_USER=frappe
   BENCH_PATH=/home/frappe/frappe-bench
   SITE_NAME=sprint.example.com
   # optional: SSH_PORT=22  SSH_KEY=~/.ssh/sprint_deploy  WEB_PORT=8000
   ```

## Merge rules (admins)

The rules live as JSON in `.github/rulesets/`. To change them, edit the JSON and run:
```bash
gh auth login
bash .github/rulesets/apply.sh          # idempotent
```
Current rules:
- `main`: PR only, 1 code-owner approval (admin bypass via PR only), merge commits only,
  stale approvals dismissed on new pushes, conversations resolved, no force-push or delete.
- `dev`: PR only, squash or merge commit, conversations resolved, no force-push or delete.
- `v*` tags: can't be moved or deleted.
- Repo: rebase-merge off, merged branches auto-deleted, GitHub Actions disabled.
