# Test patterns for the in-memory harness

All examples assume the skeleton from `SKILL.md` (app on an ephemeral port, `data.init(pool)`), plus small `get`/`post` helpers that send the test identity header. Adapt names to your code.

## Fault injection: the DB goes away after boot, the process must survive

```js
/**
 * Why: a bare async handler that rejects becomes an unhandled rejection and kills the process.
 * Asserts: a write whose query rejects returns 500 and the process keeps serving.
 */
const real = memPool();
let failQueries = false;
const pool = {
  query: (...a) => (failQueries ? Promise.reject(new Error("simulated: database unavailable")) : real.query(...a)),
  end: (...a) => real.end(...a),
};
// test.before: await data.init(pool); start the server on port 0 as in the skeleton

test("returns 500, not a crash, when the DB rejects", async () => {
  failQueries = true;
  try {
    const r = await post("/api/signup", { email: "dbdown@example.com" });
    assert.equal(r.status, 500);
    assert.equal(JSON.parse(r.body).error, "internal error", "no internals leaked");
  } finally {
    failQueries = false;
  }
});

test("recovers once the DB is back (proves the process survived)", async () => {
  assert.equal((await post("/api/signup", { email: "ok@example.com" })).status, 200);
});
```

## Multi-tenant leak guard (data layer)

```js
/** Why: the top multi-tenant risk is a forgotten owner scope. No data function may read or mutate another user's rows. */
let A, B;
test.before(async () => {
  await data.init(memPool());
  A = await data.getOrCreateUser("a@example.com");
  B = await data.getOrCreateUser("b@example.com");
});

test("unscoped calls throw instead of running unscoped", async () => {
  await assert.rejects(() => data.listItems(undefined), /userId is required/);
});

test("reads are scoped to the owner", async () => {
  const a1 = await data.addItem(A, "alpha");
  const b1 = await data.addItem(B, "beta");
  const ids = (await data.listItems(A)).map((r) => r.id);
  assert.ok(ids.includes(a1) && !ids.includes(b1));
});

test("mutations by a non-owner are no-ops", async () => {
  const a = await data.addItem(A, "original");
  await data.updateItem(B, a, "HACKED");
  await data.deleteItem(B, a);
  assert.equal((await data.listItems(A)).find((r) => r.id === a).content, "original");
});

// Also: bulk actions touch only the caller's rows; account deletion erases only the caller.
```

## CSRF guard over real HTTP (attack shapes plus a positive control)

```js
function send(path, { method = "POST", headers = {}, payload = null } = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(base + path, { method, headers: { [IDENTITY_HEADER]: EMAIL, ...headers } }, (res) => {
      let body = "";
      res.on("data", (c) => (body += c));
      res.on("end", () => resolve({ status: res.statusCode, body }));
    });
    req.on("error", reject);
    req.end(payload);
  });
}

test("cross-site form POST is rejected and deletes nothing", async () => {
  const payload = "id=";
  const r = await send("/api/items/delete", {
    headers: { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": Buffer.byteLength(payload) },
    payload,
  });
  assert.equal(r.status, 415);
  // assert the seeded item is still present
});

test("bodyless cross-site POST to the delete route is rejected", async () => {
  assert.equal((await send("/api/items/delete")).status, 415);
});

test("legitimate JSON writes still work (positive control)", async () => {
  const payload = JSON.stringify({ content: "ok" });
  const r = await send("/api/items", { headers: { "Content-Type": "application/json" }, payload });
  assert.equal(r.status, 200);
});
```

## Security headers and no inline handlers

```js
test("app shell ships a strict CSP", async () => {
  const r = await get("/app");
  const csp = r.headers["content-security-policy"] || "";
  assert.match(csp, /script-src 'self'/);
  assert.ok(!/script-src[^;]*'unsafe-inline'/.test(csp));
  for (const d of ["frame-ancestors 'none'", "object-src 'none'", "base-uri 'none'"]) assert.ok(csp.includes(d), d);
  assert.equal(r.headers["x-content-type-options"], "nosniff");
});

test("no inline event handlers in served HTML/JS", async () => {
  const re = /\son(click|error|input|keydown|change|load|submit|mouseover)=/i;
  assert.ok(!re.test((await get("/app")).body));
  assert.ok(!re.test((await get("/app.js")).body));
});
```

## Deterministic concurrency (pin the clock to force collisions)

```js
test("concurrent inserts in the same millisecond all get distinct ids", async () => {
  const realNow = Date.now;
  Date.now = () => 1_700_000_000_000;
  try {
    const ids = await Promise.all(Array.from({ length: 10 }, (_, i) => data.addItem(U, "x" + i)));
    assert.equal(new Set(ids).size, 10);
    assert.equal((await data.listItems(U)).length, 10, "none lost to a swallowed collision");
  } finally {
    Date.now = realNow;
  }
});
```

## Rules that go with every pattern

- Every guard test has a positive control, so an over-broad fix fails too.
- Every file opens with why it exists; every assertion message says what broke in user terms.
- Run the new test against the unfixed code first and watch it fail (counter-test discipline).
