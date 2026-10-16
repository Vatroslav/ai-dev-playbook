/* Assemble dist/ for static hosting when the app has no bundler. Copy to scripts/build-dist.mjs
   and use `node scripts/build-dist.mjs` as the "build" in .claude/deploy.json.
   It only copies runtime files into a clean folder, so node_modules, docs, metrics, .claude
   and tool configs never ship.
   ALLOWLIST, not denylist, on purpose: it states exactly what ships, and a stray file
   cannot leak. Keep it aligned with sw.js ASSETS and the <script>/<link> tags. */
import { rmSync, mkdirSync, copyFileSync, writeFileSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");

const FILES = [
  "index.html",
  "style.css",
  "app.js",
  "sw.js",
  "package.json", // the app fetches ./package.json to display its version
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/icon-512-maskable.png",
];

rmSync(dist, { recursive: true, force: true });
for (const rel of FILES) {
  const to = join(dist, rel);
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(join(root, rel), to); // throws if a listed file is missing - good
}

// A tiny version marker the deploy step can curl to confirm what is live.
const { version } = JSON.parse(readFileSync(join(root, "package.json"), "utf-8"));
writeFileSync(join(dist, "version.json"), JSON.stringify({ version }) + "\n");

console.log(`build-dist: copied ${FILES.length} files + version.json (${version}) to dist/`);
