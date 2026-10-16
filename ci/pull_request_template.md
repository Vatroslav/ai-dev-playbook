<!--
Copy to .github/pull_request_template.md.
The PR TITLE becomes the squash commit message: start it with a conventional type
(feat / fix / perf / docs / refactor / test / chore / ci / build / revert). CI reads the type to decide
whether a version bump is required.
Delete sections that do not apply. Do not leave the template empty.
-->

## What and why

<!-- What changes for the user or the system, and which problem it solves. Link the task ID. -->

## How it works

<!-- The approach. Call out anything non-obvious and anything a reviewer might "fix" by mistake. -->

## How it was verified

<!-- Commands you ran and their result, what you clicked through, which account(s) you used.
     For a bug fix: the test that fails on the unfixed code and passes with the fix. -->

## Checklist

- [ ] Working implementation: no stubs, `TODO`/`FIXME` markers or commented-out code
- [ ] Tests added or updated in this PR; nothing skipped, deleted or weakened to get green
- [ ] Bug fix: the new test was run against the unfixed code and failed
- [ ] Lint, typecheck (including test files) and tests pass locally
- [ ] Version bumped by intent if shipped behaviour changed (feat: minor, fix/perf: patch, breaking: major), and the PR title has the matching type
- [ ] Docs updated in this PR if a documented topic changed (README, ADR, feature doc)
- [ ] Cleanup done: dead code, unused imports, `_old` / `_v2` files removed
- [ ] No secrets, credentials, `.env` files or personal data committed; `.gitignore` not weakened
- [ ] Migrations (if any): new migration file only, tested on a fresh DB and on a copy of a pre-change DB
- [ ] Prompt or agent changes (if any): eval results before and after are in the description

## User-visible copy

<!-- Every changed user-facing string, in every locale. Auto-merge is armed only after the product
     owner said "ok" to this list. Internal admin-tool copy: list it here, no approval needed. -->

## Deviations from the design or spec

<!-- Each conscious deviation and why. If none, write "0 (implemented 1:1)". -->

## Steps for a human after merge

<!-- Production commands, settings or data steps a human must run. Each command says where it runs,
     as which account, and in which folder. No rollback command unless someone asked for one. -->

## Notes for reviewers
