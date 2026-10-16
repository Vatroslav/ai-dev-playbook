# ci/

Purpose: ready-to-copy GitHub Actions workflows, Dependabot config, PR template and the two Node scripts the CI uses.
Read when: setting up CI/CD for a new repo, or changing how PRs are checked and merged.

The rules behind these files are in [CI/CD and deploy](../docs/agent/ci-cd-and-deploy.md), [git workflow](../docs/agent/git-workflow.md) and [versioning](../docs/agent/versioning.md).

## Files and where they go

| File here | Copy to | What it does |
|---|---|---|
| `workflows/ci.yml` | `.github/workflows/ci.yml` | The one required job `check`: docs-only detection, install, optional ephemeral Postgres with a production-like role split, lint, typecheck (tests included), tests, CI script tests, build, version-by-intent check on the PR title. |
| `workflows/deploy-staging.yml` | `.github/workflows/deploy-staging.yml` | Staging deploy on every merge to main: keyless OIDC login, image tagged with the commit SHA, migrations only when the live schema lags, deploy, post-deploy smoke test. Steps named `PROVIDER-SPECIFIC` fail until you fill them in. |
| `dependabot.yml` | `.github/dependabot.yml` | Weekly grouped updates for pinned actions (and optionally npm). Not auto-merged. |
| `pull_request_template.md` | `.github/pull_request_template.md` | PR description with the merge checklist, copy gate, deviations and human steps. |
| `scripts/ci-docs-only.mjs` | `scripts/ci-docs-only.mjs` | Decides whether a PR is docs only, so `check` can skip heavy steps without being skipped itself. Fail-safe: anything unclear runs full CI. |
| `scripts/check-version-bump.mjs` | `scripts/check-version-bump.mjs` | Fails the PR when the title's conventional type needs a bump (`feat`, `fix`, `perf`, breaking) and the version did not move, when the version goes down, has a suffix, or the title has no type. |
| `scripts/*.test.mjs` | `scripts/` | `node:test` tests for both scripts. They run each script as a subprocess in a temporary git repo, the way CI runs it. |

All scripts are plain Node ESM with no dependencies (Node 18 or newer).

## Setup, in order

1. **Copy the files** to the locations in the table.
2. **Pin every action to a full commit SHA.** Each `PIN_TO_FULL_COMMIT_SHA` must become the 40-character SHA of the release you want, with the version in the trailing comment:
   ```bash
   git ls-remote --tags https://github.com/actions/checkout 'v4.*'
   ```
   For an annotated tag, git prints two lines; use the SHA on the line ending in `^{}` (the commit, not the tag object). Then write `uses: actions/checkout@<sha> # v4.x.y`. Dependabot keeps these fresh.
3. **Pin pnpm:** add `"packageManager": "pnpm@<exact version>"` to `package.json`. CI uses Corepack, so CI, cloud shells and laptops run the same pnpm.
4. **Provide the scripts CI calls** in `package.json`: `lint`, `typecheck` (`tsc --noEmit`, covering test files), `test`, `build`, and, if you keep the Postgres block, `db:migrate` and `test:db`. Delete the steps marked `OPTIONAL: Postgres` if the app has no Postgres.
5. **Keep the two test runners apart.** The script tests use `node:test`. If the repo uses Vitest, exclude them from Vitest (`exclude: [...configDefaults.exclude, "scripts/*.test.mjs"]`), or Vitest will try to run them and report "no test suite found".
6. **Run the script tests locally once:** `node --test scripts/*.test.mjs`. All must pass before you rely on the CI step.
7. **Ask the repo admin to set the repository settings below.** Agents must not change repository settings.
8. **Deploy workflow:** fill in the `PROVIDER-SPECIFIC` steps, set the variables and secret listed at the top of `deploy-staging.yml`, and make sure the app implements the health contract described there.

## Repository settings (done by a human admin, once)

- **Pull requests:** allow squash merging, allow auto-merge, automatically delete head branches.
- **Ruleset on the default branch**, with no bypass list:
  - require the status check `check`;
  - do NOT require branches to be up to date before merging (non-strict mode: no rebase treadmill for small independent PRs);
  - block force pushes;
  - restrict deletions.
- **Actions:** set the default `GITHUB_TOKEN` permission to read-only; workflows ask for more only where needed.
- **Environment `staging`:** holds the deploy variables and the health token. No production secrets anywhere in GitHub.

## Why the CI looks like this (short version)

- **One job, always running.** GitHub bills at least a minute per job, and a required check that is skipped by `paths-ignore` stays "Expected" forever, so docs-only PRs could never merge. The job always runs; heavy steps check `steps.scope.outputs.docs_only`.
- **PR-only trigger.** A squash merge of a PR that already passed `check` is the same code. The staging smoke test catches the rare semantic conflict between two green PRs.
- **Version check last.** Lint, type and test results still show when only the bump is missing.
- **The PR title goes through `env:`.** Inlining `${{ github.event.pull_request.title }}` into a `run:` block lets anyone who can open a PR inject shell commands.
- **The CI scripts test themselves.** A guard that compares `import.meta.url` with a hand-built `file:///` path never matches on Linux, so its "run as main" branch never executes and the step passes on everything. Both scripts here use `pathToFileURL`, and the tests run them as subprocesses to prove they fail when they should.
