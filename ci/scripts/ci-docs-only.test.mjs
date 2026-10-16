/**
 * Why this file exists: if the docs-only detector wrongly says "docs only", CI skips tests and
 * a broken PR merges green. These tests prove the fail-safe direction: anything unclear runs full CI.
 *
 * Run: node --test scripts/*.test.mjs
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync, execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, readFileSync, rmSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { isDocsOnly, MD_READ_BY_TESTS } from "./ci-docs-only.mjs";

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), "ci-docs-only.mjs");

/** Temp repo; if `merge` is true, HEAD is a merge commit that brings in `files`. */
function repo(files, { merge }) {
  const dir = mkdtempSync(join(tmpdir(), "docs-only-"));
  const git = (...args) => execFileSync("git", ["-c", "user.name=test", "-c", "user.email=test@example.com", ...args], { cwd: dir, stdio: "pipe" });
  git("init", "-q", "-b", "main");
  writeFileSync(join(dir, "README.md"), "base\n");
  git("add", "README.md");
  git("commit", "-q", "-m", "chore: init");
  if (merge) git("switch", "-q", "-c", "feature");
  for (const f of files) {
    mkdirSync(dirname(join(dir, f)), { recursive: true });
    writeFileSync(join(dir, f), "changed\n");
    git("add", f);
  }
  git("commit", "-q", "-m", "docs: change");
  if (merge) {
    git("switch", "-q", "main");
    git("merge", "-q", "--no-ff", "-m", "merge", "feature");
  }
  return dir;
}

function run(dir) {
  const out = join(dir, "gh-output.txt");
  writeFileSync(out, "");
  const r = spawnSync(process.execPath, [SCRIPT], { cwd: dir, encoding: "utf8", env: { ...process.env, GITHUB_OUTPUT: out } });
  return { ...r, output: readFileSync(out, "utf8") };
}

test("isDocsOnly: empty diff is not docs-only (fail-safe)", () => {
  assert.equal(isDocsOnly([]), false);
});

test("isDocsOnly: markdown only -> true; any code -> false", () => {
  assert.equal(isDocsOnly(["README.md", "docs/a.md"]), true);
  assert.equal(isDocsOnly(["README.md", "src/a.ts"]), false);
});

test("isDocsOnly: markdown that tests read triggers full CI", () => {
  for (const f of MD_READ_BY_TESTS) assert.equal(isDocsOnly([f]), false, f);
});

test("subprocess: merge commit with docs only -> docs_only=true", () => {
  const dir = repo(["docs/guide.md", "README.md"], { merge: true });
  try {
    const r = run(dir);
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /docs only/);
    assert.match(r.output, /docs_only=true/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("subprocess: merge commit touching code -> docs_only=false", () => {
  const dir = repo(["docs/guide.md", "src/app.ts"], { merge: true });
  try {
    assert.match(run(dir).output, /docs_only=false/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("subprocess: HEAD that is not a merge commit -> full CI", () => {
  const dir = repo(["docs/guide.md"], { merge: false });
  try {
    const r = run(dir);
    assert.match(r.stdout, /full CI/);
    assert.match(r.output, /docs_only=false/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
