// Telemetry collector - Google Apps Script web app.
// Receives anonymous events (POST, text/plain) and appends one row per event.
// ONE Sheet + ONE Apps Script project per app: a foreign endpoint must never receive this
// app's events (two apps with different measures would mix in one table).

const SHEET_ID = "__SHEET_ID__"; // from the Sheet URL: /d/<THIS>/edit
const SHEET_NAME = "events";

// The first columns are a CONTRACT for every reader (dashboard, any cross-app overview),
// which finds them BY NAME (ts, session, env, event). Do not rename them.
// New fields go STRICTLY AT THE END: inserting in the middle shifts data in rows that are
// already written.
const HEADER = [
  "ts",
  "session",
  "version",
  "env",
  "event",
  "payload",
  "client_ts",
  // app-specific columns, appended over time, e.g. "step", "duration_ms"
];

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    const p = d.payload || {};
    const sh = sheet();
    ensureHeader(sh);
    sh.appendRow([
      new Date(), // server timestamp
      d.session || "", // anonymous per-device id
      d.version || "",
      d.env || "", // 'dev' (local) | 'prod' (any shipped copy)
      d.event || "",
      JSON.stringify(p), // full payload: fields without their own column are not lost
      d.ts || "", // client timestamp (ms)
      // app-specific values, same order as the extra HEADER columns, e.g. num(p.step)
    ]);
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, err: String(err) });
  }
}

// Empty cell (not 0/false) when a field does not belong to the event - otherwise every
// app_opened row looks like a session with zero actions and ruins the averages.
// eslint-disable-next-line no-unused-vars
function num(v) {
  return typeof v === "number" ? v : "";
}

// One doGet per project (Apps Script allows only one): ?health=1 returns collector health
// as JSON; everything else serves the dashboard (dashboard.js + Index.html).
function doGet(e) {
  if (e && e.parameter && e.parameter.health != null) return health_();
  return dashboardHtml_();
}

// Counts only - the endpoint is public, so row contents never go out.
function health_() {
  try {
    const sh = sheet();
    const rows = Math.max(0, sh.getLastRow() - 1);
    const tz = {
      tzSheet: sh.getParent().getSpreadsheetTimeZone(),
      tzScript: Session.getScriptTimeZone(),
      now: String(new Date()),
    };
    if (!rows) return json({ ok: true, rows: 0, ...tz });
    const last = sh.getRange(sh.getLastRow(), 1, 1, 5).getValues()[0];
    const tally = {};
    for (const [ev] of sh.getRange(2, 5, rows, 1).getValues()) tally[ev] = (tally[ev] || 0) + 1;
    return json({ ok: true, rows, last: String(last[0]), env: last[3], event: last[4], tally, ...tz });
  } catch (err) {
    return json({ ok: false, err: String(err) });
  }
}

// Run ONCE from the editor (Run -> probe). It triggers the deploying account's OAuth consent
// (without it the web app answers 403 to everyone) and writes a probe row, which proves writing
// works. The row may be deleted.
// eslint-disable-next-line no-unused-vars
function probe() {
  const sh = sheet();
  ensureHeader(sh);
  sh.appendRow([new Date(), "probe", "", "test", "probe"]);
  return "ok: " + sh.getName() + ", rows: " + sh.getLastRow();
}

// Creates the tab if missing (a fresh Sheet's first tab has a default name and would
// silently reject every event). Also aligns the Sheet timezone with the script's: a Sheet
// created by tooling can default to another zone, which shifts daily charts by one day
// while everything "looks healthy".
function sheet() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const tz = Session.getScriptTimeZone();
  if (ss.getSpreadsheetTimeZone() !== tz) ss.setSpreadsheetTimeZone(tz);
  return ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
}

// The header is rewritten when HEADER grows; old rows stay untouched (empty new columns).
function ensureHeader(sh) {
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADER);
    sh.getRange(1, 1, 1, HEADER.length).setFontWeight("bold");
    sh.setFrozenRows(1);
    return;
  }
  const cur = sh.getRange(1, 1, 1, HEADER.length).getValues()[0];
  if (cur.join(" ") === HEADER.join(" ")) return;
  sh.getRange(1, 1, 1, HEADER.length).setValues([HEADER]).setFontWeight("bold");
  sh.setFrozenRows(1);
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
