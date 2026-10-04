## What & why
<!-- What does this change, and why? Link the issue/card if there is one. -->

## Type
- [ ] Feature (→ `dev`)
- [ ] Fix (→ `dev`)
- [ ] Release (`dev` → `main`)
- [ ] Hotfix (→ `main`, back-merge to `dev` afterwards)

## Checklist
- [ ] Ran the server tests locally (`run-tests --module sprint.tests.test_api` / `test_automation`)
- [ ] `pre-commit` passes (ruff, eslint, prettier)
- [ ] `frontend/src` changed → rebuilt with `yarn build` and committed `sprint/public/frontend` + `sprint/www/sprint.html`
- [ ] Schema change → added as an idempotent `ensure_*` in `sprint/setup.py` (runs on `migrate`)
- [ ] Card writes go through Sprint's endpoints (`sprint/api.py`), not raw DB writes
- [ ] Tested against `Dev Task` (never destructive tests on `Analyst Space`)

## How to verify
<!-- Steps a reviewer can follow on staging / a local bench. -->
