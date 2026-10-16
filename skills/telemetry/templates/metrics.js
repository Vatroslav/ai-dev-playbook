/* Anonymous product telemetry - web client.
   Principles: never crashes the app (everything in try/catch), never blocks
   (fire-and-forget), no PII (anonymous per-device id), NO-OP while ENDPOINT is empty.

   Works with both collector options from the telemetry skill:
   - own backend: POST /api/events, body = JSON sent as text/plain
   - Apps Script web app: the .../exec URL
   text/plain + mode "no-cors" makes a "simple request" with no CORS preflight (Apps Script
   does not answer preflights). The response is unreadable and not needed.

   Load it before the app code with a classic <script> tag, or import it once; it exposes
   window.Metrics.track(event, payload). */
(() => {
  "use strict";

  /** Collector URL. Empty = tracking off. Not a secret (visible in the network tab anyway).
      One endpoint per app: never share a collector between apps. */
  const ENDPOINT = "";
  /** localStorage key for the anonymous device id. Make it unique per app. */
  const SID_KEY = "myapp_sid";
  /** Payload keys allowed in prod (null = send the full payload). Keep prod payloads to
      non-sensitive numbers and enums; send richer payloads only to a local dev collector. */
  const PROD_KEYS = null; // e.g. ["step", "duration_ms", "result"]

  // dev = what the team runs itself (local dev server / file://), prod = every shipped copy.
  // Deliberately NOT a list of production hosts: hosts, embeds and CDNs change domains and
  // a host list silently breaks; "not a local host" is checkable.
  const LOCAL_HOSTS = ["localhost", "127.0.0.1", "[::1]", "::1"];
  function env() {
    try {
      const h = location.hostname;
      if (!h || LOCAL_HOSTS.includes(h) || h.endsWith(".local") || h.endsWith(".localhost")) return "dev"; // file:// has no hostname
      return "prod";
    } catch {
      return "prod";
    }
  }

  function uuid() {
    try {
      if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
    } catch {
      /* fall through */
    }
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
  }

  function sessionId() {
    try {
      let id = localStorage.getItem(SID_KEY);
      if (!id) {
        id = uuid();
        localStorage.setItem(SID_KEY, id);
      }
      return id;
    } catch {
      // Private mode / blocked storage: still send, just without recognising returners.
      // Silently dropping out of the numbers would be worse than an anonymous row.
      return "nostore";
    }
  }

  // Version read once from package.json (single source of truth). If the build injects a
  // version constant (e.g. __APP_VERSION__), return that instead and skip the fetch.
  let versionP = null;
  function version() {
    if (!versionP) {
      versionP = fetch("./package.json")
        .then((r) => r.json())
        .then((p) => (p && p.version) || "")
        .catch(() => "");
    }
    return versionP;
  }

  function narrow(payload, e) {
    if (e !== "prod" || !PROD_KEYS) return payload;
    const out = {};
    for (const k of PROD_KEYS) if (k in payload) out[k] = payload[k];
    return out;
  }

  function send(body) {
    fetch(ENDPOINT, {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "text/plain;charset=UTF-8" },
      body: JSON.stringify(body),
      keepalive: true, // survives tab close - needed for "left" events sent on pagehide
    }).catch(() => {});
  }

  /** Send one event. `payload` = non-sensitive numbers and enums (step, duration, result). */
  function track(event, payload) {
    if (!ENDPOINT) return;
    try {
      const e = env();
      const base = { session: sessionId(), env: e, event, payload: narrow(payload || {}, e), ts: Date.now() };
      version()
        .then((v) => send({ ...base, version: v }))
        .catch(() => {});
    } catch {
      /* tracking must never crash the app */
    }
  }

  window.Metrics = { track, uuid, env };
})();
