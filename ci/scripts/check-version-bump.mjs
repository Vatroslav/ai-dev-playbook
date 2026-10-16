#!/usr/bin/env node
/**
 * Version-by-intent check for CI. Layer 2 behind the agent's local commit hook
 * (hooks/check-version-bump.sh). The hook only sees commits made through the agent;
 * manual commits, other tools, server-side merges and `--no-verify` bypass it.
 *
 * The PR title becomes the squash commit message, so its conventional type decides:
 *   feat / fix / perf, or breaking (`type!:` or a `BREAKING CHANGE:` footer) -> version must be > base
 *   docs / chore / refactor / style / test / ci / build / revert            -> version must be >= base
 *   no recognised type                                                     -> fail
 * Always: clean SemVer X.Y.Z (no "v" prefix, no "-1" suffix), and the version never goes down.
 * The bump LEVEL (minor vs patch) is not checked: CI must not be stricter than the local hook.
 *
 * Inputs (environment variables):
 *   PR_TITLE      the PR title. Pass it through `env:`; never inline `${{ ... }}` into `run:` (script injection).
 *   HEAD_VERSION  optional; default: VERSION_FILE read from the working tree.
 *   BASE_VERSION  optional; default: VERSION_FILE read from BASE_REF with `git show`.
 *   BASE_REF      optional; default `HEAD^1` = first parent of the PR merge commit = the base branch.
 *                 Needs `fetch-depth: 2` on actions/checkout.
 *   VERSION_FILE  optional; default `package.json`. A *.json file with a "version" field,
 *                 or a plain-text file whose first line is X.Y.Z (e.g. VERSION).
 *
 * Run: `node scripts/check-version-bump.mjs`. Exit 0 = ok, exit 1 = fail (GitHub `::error::` annotation).
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const SEMVER = /^(\d+)\.(\d+)\.(\d+)$/;
export const BUMP_TYPES = new Set(["feat", "fix", "perf"]);
export const NO_BUMP_TYPES = new Set(["docs", "chore", "refactor", "style", "test", "ci", "build", "revert"]);

/** "1.2.3" -> [1, 2, 3]; anything else (suffix, prefix, empty) -> null. */
export function parseSemver(value) {
  const m = SEMVER.exec(String(value ?? "").trim());
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

export function compareSemver(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] - b[i];
  return 0;
}

/** Conventional type from the FIRST line only; breaking via `type!:` or a BREAKING CHANGE footer. */
export function parseIntent(title) {
  const text = String(title ?? "");
  const header = text.split(/\r?\n/)[0].trim();
  const m = /^([a-zA-Z]+)(\([^)]*\))?(!)?:/.exec(header);
  return {
    header,
    type: m ? m[1].toLowerCase() : null,
    breaking: Boolean(m && m[3]) || /^BREAKING[ -]CHANGE:/m.test(text),
  };
}

/** Pure decision. `title === null` means "no PR title available": only format and direction are checked. */
export function checkVersionBump({ base, head, title, file = "package.json" }) {
  const h = parseSemver(head);
  if (!h) return { ok: false, message: `version "${head}" in ${file} is not clean SemVer X.Y.Z (no "v" prefix, no suffix).` };

  const b = parseSemver(base);
  if (!b) return { ok: true, message: `base version "${base}" is not clean SemVer (or absent); only the branch version ${head} was checked.` };

  const delta = compareSemver(h, b);
  if (delta < 0) return { ok: false, message: `version went down: ${base} -> ${head}. Versions never decrease.` };

  if (title === null) return { ok: true, message: `version ${head} (base ${base}); no PR title given, intent not checked.` };

  const { header, type, breaking } = parseIntent(title);
  if (type === null || !(BUMP_TYPES.has(type) || NO_BUMP_TYPES.has(type))) {
    const allowed = [...BUMP_TYPES, ...NO_BUMP_TYPES].join(", ");
    return { ok: false, message: `PR title "${header}" has no conventional type (${allowed}). The title becomes the squash commit message.` };
  }
  if ((breaking || BUMP_TYPES.has(type)) && delta === 0) {
    const what = breaking ? "breaking change" : `type "${type}"`;
    return { ok: false, message: `${what} but the version stayed ${head}. Bump ${file} in this PR (feat -> minor, fix/perf -> patch, breaking -> major).` };
  }
  return {
    ok: true,
    message: delta > 0 ? `bumped ${base} -> ${head} ("${type}").` : `version stays ${head} ("${type}" needs no bump).`,
  };
}

/** Version string from file content: JSON "version" field, or the first line of a plain-text file. */
export function readVersion(content, file) {
  if (file.endsWith(".json")) return String(JSON.parse(content).version ?? "");
  return content.split(/\r?\n/)[0].trim();
}

function fail(message) {
  console.error(`::error::check-version-bump: ${message}`);
  process.exit(1);
}

// pathToFileURL, NOT a hand-built "file://" + path: on Linux that string never equals
// import.meta.url, so the script would exit 0 without checking anything.
const isMain = Boolean(process.argv[1]) && import.meta.url === pathToFileURL(process.argv[1]).href;

if (isMain) {
  const file = process.env.VERSION_FILE || "package.json";
  let head = process.env.HEAD_VERSION;
  let base = process.env.BASE_VERSION;

  if (head === undefined) {
    try {
      head = readVersion(readFileSync(file, "utf8"), file);
    } catch (e) {
      fail(`cannot read the version from ${file} in the working tree: ${e.message}`);
    }
  }

  if (base === undefined) {
    const ref = process.env.BASE_REF || "HEAD^1";
    try {
      const content = execFileSync("git", ["show", `${ref}:${file}`], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
      base = readVersion(content, file);
    } catch (e) {
      const stderr = String(e.stderr ?? e.message);
      if (/does not exist in|exists on disk, but not in/.test(stderr)) {
        base = ""; // the version file is new in this PR: nothing to compare against
      } else {
        // Fail loudly: silently skipping the comparison would make this step green on everything.
        fail(`cannot read ${file} at ${ref} (${stderr.trim()}). In CI, check out the PR merge commit with fetch-depth: 2, or set BASE_VERSION.`);
      }
    }
  }

  const title = process.env.PR_TITLE === undefined ? null : process.env.PR_TITLE;
  const result = checkVersionBump({ base, head, title, file });
  if (!result.ok) fail(result.message);
  console.log(`check-version-bump: ${result.message}`);
}
