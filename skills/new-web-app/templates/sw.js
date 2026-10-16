/* Service worker: network-first that BYPASSES the HTTP cache.
   Online = always fresh; the cache is an offline fallback only.
   CACHE is an internal name, NOT the app version: no bump is needed per release.
   Keep ASSETS aligned with the files your index.html actually loads. */
const CACHE = "app-cache-v1";
const ASSETS = ["./", "./index.html", "./style.css", "./app.js", "./package.json", "./manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      .then((c) =>
        Promise.all(ASSETS.map((url) => fetch(url, { cache: "reload" }).then((r) => c.put(url, r)).catch(() => {}))),
      )
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const sameOrigin = new URL(e.request.url).origin === self.location.origin;
  // cache: "no-cache" = revalidate with the server (304 if unchanged). Without it the
  // browser HTTP cache can serve an old data file next to a new app file: half old,
  // half new version.
  e.respondWith(
    fetch(e.request, { cache: "no-cache" })
      .then((resp) => {
        // Only successful same-origin responses become offline copies (never cache a 404).
        if (resp.ok && sameOrigin) {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        }
        return resp;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match("./index.html"))),
  );
});
