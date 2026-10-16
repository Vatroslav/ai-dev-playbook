/**
 * Why this file exists: a CI guard that exits 0 on everything looks exactly like a guard that
 * passes. These tests run the script the way CI runs it (a subprocess, in a real git repo with
 * a PR-style merge commit) and prove that it fails when it should.
 *
 * Run: node --test scripts/*.test.mjs
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync, execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { checkVersionBump, parseIntent, parseSemver } from "./check-version-bump.mjs";

const SCRIPT = join(dirname(fileURLToPath(import.meta.url)), "check-version-bump.mjs");

function run(env, cwd = process.cwd()) {
  const clean = { ...process.env };
  for (const k of ["PR_TITLE", "HEAD_VERSION", "BASE_VERSION", "BASE_REF", "VERSION_FILE"]) delete clean[k];
  return spawnSync(process.execPath, [SCRIPT], { cwd, encoding: "utf8", env: { ...clean, ...env } });
}

/** Temp repo whose HEAD is a merge commit: first parent = base (baseVersion), working tree = branch (headVersion). */
function repoWithMerge(baseVersion, headVersion) {
  const dir = mkdtempSync(join(tmpdir(), "version-check-"));
  const git = (...args) => execFileSync("git", ["-c", "user.name=test", "-c", "user.email=test@example.com", ...args], { cwd: dir, stdio: "pipe" });
  git("init", "-q", "-b", "main");
  writeFileSync(join(dir, "package.json"), JSON.stringify({ name: "x", version: baseVersion }) + "\n");
  git("add", "package.json");
  git("commit", "-q", "-m", "chore: init");
  git("switch", "-q", "-c", "feature");
  writeFileSync(join(dir, "package.json"), JSON.stringify({ name: "x", version: headVersion }) + "\n");
  writeFileSync(join(dir, "a.txt"), "change\n");
  git("add", "package.json", "a.txt");
  git("commit", "-q", "-m", "feat: change");
  git("switch", "-q", "main");
  git("merge", "-q", "--no-ff", "-m", "merge", "feature");
  return dir;
}

test("subprocess: feat without a bump exits 1 with an annotation", () => {
  const r = run({ HEAD_VERSION: "0.5.0", BASE_VERSION: "0.5.0", PR_TITLE: "feat: x" });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /::error::/);
});

test("subprocess: docs without a bump exits 0 and says why", () => {
  const r = run({ HEAD_VERSION: "0.5.0", BASE_VERSION: "0.5.0", PR_TITLE: "docs: x" });
  assert.equal(r.status, 0, r.stderr);
  assert.match(r.stdout, /version stays 0\.5\.0/);
});

test("subprocess: reads both versions from git when env is not set", () => {
  const dir = repoWithMerge("1.2.0", "1.3.0");
  try {
    const ok = run({ PR_TITLE: "feat: new thing" }, dir);
    assert.equal(ok.status, 0, ok.stderr);
    assert.match(ok.stdout, /bumped 1\.2\.0 -> 1\.3\.0/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("subprocess: fails loudly when the base cannot be read (no silent pass)", () => {
  const dir = mkdtempSync(join(tmpdir(), "version-check-"));
  try {
    execFileSync("git", ["init", "-q", "-b", "main"], { cwd: dir });
    writeFileSync(join(dir, "package.json"), JSON.stringify({ version: "1.0.0" }));
    execFileSync("git", ["-c", "user.name=test", "-c", "user.email=test@example.com", "add", "package.json"], { cwd: dir });
    execFileSync("git", ["-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-q", "-m", "chore: init"], { cwd: dir });
    const r = run({ PR_TITLE: "feat: x" }, dir); // HEAD^1 does not exist
    assert.equal(r.status, 1);
    assert.match(r.stderr, /fetch-depth: 2/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("parseSemver rejects suffixes and prefixes", () => {
  assert.deepEqual(parseSemver("1.2.3"), [1, 2, 3]);
  assert.equal(parseSemver("0.2.0-1"), null);
  assert.equal(parseSemver("v0.2.0"), null);
  assert.equal(parseSemver(""), null);
});

test("parseIntent: type from the first line; breaking via ! or footer", () => {
  assert.equal(parseIntent("fix(auth): x").type, "fix");
  assert.equal(parseIntent("fix!: x").breaking, true);
  assert.equal(parseIntent("feat: x\n\nBREAKING CHANGE: y").breaking, true);
  assert.equal(parseIntent("docs: explain the BREAKING CHANGE policy").breaking, false);
});

test("feat/fix/perf/breaking need a bump", () => {
  for (const title of ["feat: x", "fix: x", "perf: x", "chore!: x"]) {
    assert.equal(checkVersionBump({ base: "0.2.0", head: "0.2.0", title }).ok, false, title);
    assert.equal(checkVersionBump({ base: "0.2.0", head: "0.3.0", title }).ok, true, title);
  }
});

test("non-runtime types pass without a bump", () => {
  for (const t of ["docs", "chore", "refactor", "style", "test", "ci", "build", "revert"]) {
    assert.equal(checkVersionBump({ base: "0.2.0", head: "0.2.0", title: `${t}: x` }).ok, true, t);
  }
});

test("version never decreases, whatever the type", () => {
  assert.equal(checkVersionBump({ base: "0.3.0", head: "0.2.9", title: "docs: x" }).ok, false);
});

test("missing or unknown type fails", () => {
  assert.equal(checkVersionBump({ base: "0.2.0", head: "0.2.0", title: "Fix the table" }).ok, false);
  assert.equal(checkVersionBump({ base: "0.2.0", head: "0.2.0", title: "wip: stuff" }).ok, false);
});

test("suffix on the branch version fails", () => {
  assert.equal(checkVersionBump({ base: "0.2.0", head: "0.3.0-1", title: "feat: x" }).ok, false);
});
