#!/usr/bin/env node
/**
 * Is this PR documentation only? If yes, the required `check` job skips install, database,
 * tests and build, but still runs (and still runs the version check).
 *
 * Why not `paths-ignore` on the workflow: `check` is a required status check. A workflow that
 * does not run leaves the check "Expected" forever and the PR cannot merge. So the job always
 * runs and heavy steps use `if: steps.scope.outputs.docs_only != 'true'`.
 *
 * Measures the PR merge commit (HEAD) against its first parent (the base branch). Needs
 * `fetch-depth: 2` on actions/checkout. Fail-safe: anything unclear -> full CI. That covers an
 * empty diff, HEAD that is not a merge commit, a git error, and markdown that tests or the build read.
 *
 * Output: prints the decision and appends `docs_only=true|false` to $GITHUB_OUTPUT.
 */
import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

/**
 * Markdown files that tests, the build or the app read (rendered content, fixtures, docs that
 * a consistency test parses). Changing one of them can break a test, so it triggers full CI.
 * Keep this list honest: add an entry the day a test starts reading a .md file.
 */
export const MD_READ_BY_TESTS = [
  // "docs/architecture-facts.md",
];

export function isDocsOnly(files) {
  return files.length > 0 && files.every((f) => f.endsWith(".md") && !MD_READ_BY_TESTS.includes(f));
}

/** Files changed by the PR, or null when that cannot be determined safely. */
export function changedFiles() {
  try {
    const parents = execFileSync("git", ["rev-list", "--parents", "-n", "1", "HEAD"], { encoding: "utf8" }).trim().split(" ");
    if (parents.length !== 3) return null; // commit + two parents, otherwise not a PR merge commit
    return execFileSync("git", ["diff", "--name-only", "--no-renames", "HEAD^1", "HEAD"], { encoding: "utf8" })
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  } catch {
    return null;
  }
}

// pathToFileURL, NOT a hand-built "file://" + path: on Linux that string never equals
// import.meta.url, and the script would silently do nothing in CI.
const isMain = Boolean(process.argv[1]) && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isMain) {
  const files = changedFiles();
  const docsOnly = files !== null && isDocsOnly(files);
  console.log(
    files === null
      ? "ci-docs-only: diff unreadable or HEAD is not a PR merge commit -> full CI"
      : `ci-docs-only: ${files.length} file(s) changed -> ${docsOnly ? "docs only, heavy steps skipped" : "full CI"}`,
  );
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `docs_only=${docsOnly}\n`);
}
