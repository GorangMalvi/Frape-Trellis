# Contributing & release process

How code moves from a laptop to production. The rules below are **enforced by
GitHub** (rulesets in `.github/rulesets/`), not just convention.

## Branches

| Branch | Purpose | Deploys to | Direct push |
|---|---|---|---|
| `main` | Production. Every commit is releasable. | **production** (after approval) | ❌ PR only |
| `dev` | Integration. Features land here first. | **staging** | ❌ PR only |
| `feat/*`, `fix/*`, `chore/*` | One change each, branched from `dev` | — | ✅ |
| `hotfix/*` | Urgent production fix, branched from `main` | — | ✅ |

`dev` is the default branch, so new PRs target it automatically.

## Everyday flow

```bash
git switch dev && git pull
git switch -c feat/calendar-drag        # or fix/…, chore/…
# …work, commit…
git push -u origin feat/calendar-drag
gh pr create --base dev --fill          # or open the PR on github.com
```

1. CI runs on the PR: **Lint**, **Frontend build**, **Server tests**. All three must pass.
2. Resolve all review conversations.
3. **Squash-merge** into `dev` (one clean commit per feature). The branch is auto-deleted.
4. The merge to `dev` re-runs CI and deploys to **staging**.

## Releasing to production

```bash
gh pr create --base main --head dev --title "Release v0.2.0"
```

1. Open a PR **`dev` → `main`**. It must be up to date with `main`, CI must pass, and it
   needs **1 approving review** (code owners). Admins can bypass the approval for
   solo work, but only through a PR. Nobody can push to `main` directly.
2. Merge with a **merge commit**, never squash, so `dev` and `main` keep a shared history
   and the next release doesn't conflict.
3. The push to `main` runs CI, then the **production** deploy waits for a reviewer to
   approve it under *Actions → Deploy*.
4. Tag the release (tags are the rollback points):
   ```bash
   # bump __version__ in sprint/__init__.py in the release PR first
   git switch main && git pull
   git tag -a v0.2.0 -m "v0.2.0" && git push origin v0.2.0
   ```
   `release.yml` checks that the tag is on `main` and matches `__version__`, then
   publishes a GitHub Release with generated notes. Release tags can't be moved or deleted.

## Hotfixes

```bash
git switch main && git pull && git switch -c hotfix/login-loop
# fix, push, PR → main (same checks + approval as a release), merge commit
```
Afterwards, open a PR **`main` → `dev`** (merge commit) so the fix isn't lost on the
next release.

## Rollback

*Actions → Deploy → Run workflow* (from `main`): choose `production` and a previous tag
(e.g. `v0.1.0`). That ref is checked out on the server and migrated. Database migrations
aren't reversed automatically. Every deploy takes a backup first
(`sites/<site>/private/backups`).

## What a deploy does (`.github/scripts/deploy.sh`, over SSH)

backup (DB + files) → maintenance mode on → checkout the exact commit →
`bench setup requirements` → `bench migrate` (runs the `ensure_*` hooks) →
`bench build --app sprint` → `bench restart` → maintenance off → HTTP health check
(`/api/method/ping`). If any step fails, the code is restored to the previous
commit automatically.

The frontend is **prebuilt and committed**, so servers never run `yarn build`. If you
touch `frontend/src`, rebuild (inside the devcontainer) and commit
`sprint/public/frontend` + `sprint/www/sprint.html` in the same PR. CI warns when they're stale.

## One-time setup

### Merge rules & repo settings
```bash
gh auth login
bash .github/rulesets/apply.sh          # idempotent; re-run after editing the JSON
```
This sets: rulesets for `main`, `dev` and `v*` tags; squash + merge-commit allowed
(rebase off); auto-delete merged branches; the `staging` (dev, main) and `production`
(main only, owner approval required) environments.

### Turning on deploys (per server)
1. On the server, set up a production bench (`bench setup production <user>`) with
   `apps/sprint` cloned from this repo using a **read-only deploy key**.
2. Create an SSH key pair for GitHub Actions and add the public key to the server user's
   `~/.ssh/authorized_keys`.
3. In *Settings → Environments → staging / production*, add **secrets**:

   | Secret | Example |
   |---|---|
   | `SSH_HOST` | `203.0.113.10` |
   | `SSH_USER` | `frappe` |
   | `SSH_PRIVATE_KEY` | the private key from step 2 |
   | `SSH_KNOWN_HOSTS` | output of `ssh-keyscan -p 22 203.0.113.10` |
   | `BENCH_PATH` | `/home/frappe/frappe-bench` |
   | `SITE_NAME` | `sprint.example.com` |

   Optional environment **variables**: `SSH_PORT` (22), `WEB_PORT` (8000).
4. In *Settings → Secrets and variables → Actions → Variables*, set
   `STAGING_DEPLOY_ENABLED=true` and/or `PRODUCTION_DEPLOY_ENABLED=true`.
   Until then, pushes still run CI and the deploy job is skipped.

## Local checks

```bash
pre-commit install        # ruff, eslint, prettier on commit
```
Run the server tests in your bench (see `COMMANDS.md`) before opening a PR.
