# Versioning and release notes

Purpose: one versioning model for every app: when the version moves, where it lives, how it is enforced, when it is tagged, and how release notes are written.
Read when: before a commit that changes shipped behaviour, when the version hook or the CI version check blocks you, before tagging, or when writing release notes.

## The model: bump by intent

The version moves only when shipped behaviour changes. The commit type declares the intent, and the intent decides the bump.

| Commit type | Bump | Example |
|---|---|---|
| `feat` | minor: 1.4.2 -> 1.5.0 | new screen, new endpoint, new option |
| `fix`, `perf` | patch: 1.4.2 -> 1.4.3 | bug fix, faster query |
| breaking: `type!:` or a `BREAKING CHANGE:` footer | major: 1.4.2 -> 2.0.0 | removed endpoint, incompatible data format |
| `docs`, `chore`, `refactor`, `style`, `test`, `ci`, `build`, `revert` | none, even when they touch source | rename, release-notes data file, test only |

- **Bump by hand, in the same commit as the behaviour change.** Not in a follow-up commit, not in a "Release vX" commit. Why: the commit that changes behaviour and the number that announces it must land together; a separate release commit is not a conventional type and gets blocked.
- **When the level is unclear (minor or patch), ask the product owner.** Neither the hook nor CI checks the level, only that a bump happened.
- **No release automation that computes versions** (semantic-release, changesets). Why: the agent already declares the intent in the commit type; CI-computed versions add moving parts and bot commits for no gain on a small team.
- **Data files the code imports count as source.** A changed lookup table or message catalog that changes what users see is a `feat` or `fix`, not `chore`.
- **The number tracks deployed code, not how important an announcement feels.** A big marketing moment with no code change gets no bump; a one-line fix gets a patch.
- **Prototypes may skip the version guard until they prove they will live on.** Turn the guard on the day the app gets its first real user.

## One source, plus the commit SHA

- **Keep one source of truth for the version** (`package.json` for JS apps, `versionName` in `app/build.gradle.kts` for Android, a plain `VERSION` file for a polyglot monorepo) and inject it into the build. The running app must show its own version.
  - Server or Next.js: static import, `import pkg from "@/package.json"`.
  - Vite: `define: { __APP_VERSION__: JSON.stringify(pkg.version) }`. Restart the dev server after a bump: `define` is evaluated once at config load, so the UI keeps showing the old number.
  - No bundler: stamp the version into `dist/` at build time.
- **Expose the short commit SHA next to the version: in the health endpoint and in the UI** (a tooltip or `data-` attribute, so the visible label stays a clean `vX.Y.Z`). The SHA comes from a runtime env var such as `APP_SHA`, set by the deploy. Why: once you stop bumping on every commit, two deploys can share a number, and only the SHA answers "is my change live?". See [CI/CD and deploy](ci-cd-and-deploy.md#health-endpoint).
- **If the version must live in two files, bump both, and enforce the match mechanically.** Typical case: a single-file web build of a native app with a hard-coded `const VERSION`. Configure the hook's mirror check, or add a test that compares the two. Why: the guard watches one file, and the second copy silently drifts.
- **A service worker's cache name is internal, not the app version.** With network-first fetching it never needs a bump.

## Enforcement: two layers

| Layer | File | Covers | Blind spot |
|---|---|---|---|
| Agent hook (PreToolUse on `git commit`) | [check-version-bump hook](../../hooks/check-version-bump.sh) | every commit the agent makes, before it happens | manual commits, other tools, `--no-verify`, server-side merges |
| CI step on the PR title | [check-version-bump script](../../ci/scripts/check-version-bump.mjs) in [ci.yml](../../ci/workflows/ci.yml) | every PR, whoever made it | none for main, if `check` is a required status check |

- **The hook blocks a source-touching commit with no conventional type, and a `feat` / `fix` / `perf` / breaking commit without a version bump.** Other types pass. It reads the message from `-m` or `-F <file>`; see [git workflow](git-workflow.md#staging-and-committing) for the forms it can read. Every block names the exact reason and the fix. Why: a guard that blocks valid commits with a vague message gets switched off.
- **CI reads the PR title, because the title becomes the squash commit message.** It requires: a known conventional type; version > base for bump types; version >= base for the rest; clean `X.Y.Z` with no prefix or suffix.
- **CI is never stricter than the local hook.** It doesn't check the bump level either. Why: a CI rule the agent can't see while working only produces red PRs and frustration.
- **Never bypass either layer.** If the hook blocks you, fix the commit (add the type, stage the bump, use `-m`). If you believe the hook is wrong, report it.

## Rules about the number itself

- **The version never decreases.** Both layers fail on a decrease.
- **No suffixes on main** (`1.4.0-1`, `1.4.0-test`). Strip test suffixes before merging. CI blocks them.
- **Version numbers are not checked for uniqueness.** Compute the next one from `origin/main` plus all open PR branches (command in [git workflow](git-workflow.md#before-you-start-a-task)). On a feature branch, bump once, at merge time. When parallel PRs keep colliding on the version line, merge them one at a time.
- **1.0.0 is a conscious milestone** (for example "the old system is switched off" or "first paying customer"), declared by the product owner, not reached by counting.

## Tags and releases

- **Tag only when the version reaches users:** production deploy or store upload. The tag equals the deployed number. Staging deploys are not tagged.
- **Let the production deploy script create the tag.** If the script skipped it, tag the SHA that the production health endpoint reports as live, not current main.
- **Skipped numbers are normal.** A version that went to staging but never to production simply doesn't get a tag. Never recycle a number.
- **Same number deployed twice** (a docs-only change went out with the next prod deploy): move the tag to the latest production SHA. That is the only allowed mutation of a published ref.
- **Create the git tag and the GitHub release together**, never one without the other:
  ```bash
  git tag v1.5.0 <prod-sha> && git push origin v1.5.0
  gh release create v1.5.0 --title "v1.5.0 - <short description>" --notes "<user-facing summary>"
  ```

## Android and store builds

- **`versionCode` +1 on every `versionName` bump and on every re-upload of the same version.** Why: the store rejects an upload whose `versionCode` is not higher than the last one.
- **`versionName` is always the full `X.Y.Z`.**
- **Name build artifacts `<AppName>-v<X.Y.Z>.apk`** (or `.aab`), so a file found later says what it is.
- **Browser extensions:** raise the manifest version for every store upload.

## No CHANGELOG file

- **Don't keep a `CHANGELOG.md`.** The technical trail is the conventional, scoped git history. User-facing release notes are a curated projection of it, written once. Why: two hand-maintained histories always disagree.

## Release notes

- **Draft from git, never from memory.** Material is the commits between the previous and the new production tag:
  ```bash
  git log --oneline v1.4.0..v1.5.0 | grep -E "^[0-9a-f]+ (feat|fix|perf)"
  ```
- **Include only what users actually experienced.** Exclude changes behind flags that are off in production, admin tooling, infrastructure, analytics, and fixes for bugs that never existed in production (check the old tag's code).
- **Read version and date from git:** `git show <sha>:package.json | grep '"version"'` and `git log -1 --format=%cs <sha>`. The date is the day users could first see the change, which is the production go-live, not the staging deploy.
- **Describe the user benefit, not the implementation:** "Reports load faster", not "added a 300 s TTL cache". One line per change; merge related commits into one self-contained sentence. Categories such as New / Improved / Fixed.
- **Forward-only:** no backfilled history, no recap of the whole app.
- **The product owner approves the draft in chat before it is committed to any branch that merges**: every locale, category, version and date. Edits to existing notes need approval too. Never "commit it and look on staging".
- **Commit the note before the production deploy, so it ships in the same build.** Use `docs(release-notes): ...`, which needs no bump. If the deploy slips a day, fix the date.
- **Announcements of data corrections say since when and by how much.**
