// Telemetry dashboard. Lives in the SAME Apps Script project as the collector (Code.js) and
// must NOT redeclare SHEET_ID / SHEET_NAME - a duplicate `const` breaks the whole project.
// The entry point is doGet in Code.js. Deploy as a SEPARATE web-app deployment: the
// collector URL is baked into the app, so its deployment is never touched.
//
// Rules:
//  - getData returns AGGREGATES ONLY. The URL is public; raw session ids never leave.
//  - Always filter env === 'prod', or the team's own testing looks like traffic.
//  - Days before an event first appeared are null (the page draws a dash): it was not
//    zero, it was not measured.

var EVENTS = ["app_opened", "task_started", "task_finished", "task_left"]; // funnel order
var START_EVENT = "task_started"; // "a new attempt/use started"
var DONE_EVENT = "task_finished"; // "completed"; "" if the app has no completion
var USE_MY_IDS = false; // skip the team's own session ids listed in tab "my ids" (column A from row 2)
var MY_IDS_SHEET = "my ids";

// eslint-disable-next-line no-unused-vars
function dashboardHtml_() {
  return HtmlService.createHtmlOutputFromFile("Index")
    .setTitle("Telemetry")
    .addMetaTag("viewport", "width=device-width, initial-scale=1");
}

// eslint-disable-next-line no-unused-vars
function getData() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var tz = ss.getSpreadsheetTimeZone() || Session.getScriptTimeZone();
  var sh = ss.getSheetByName(SHEET_NAME);
  var last = sh ? sh.getLastRow() : 0;
  if (!sh || last < 2) return emptyPayload_(tz);

  // Columns are found BY NAME - apps add columns over time, fixed indexes would silently
  // point at the wrong field.
  var header = sh
    .getRange(1, 1, 1, sh.getLastColumn())
    .getValues()[0]
    .map(function (h) {
      return String(h).trim();
    });
  var idx = {};
  var missing = [];
  ["ts", "session", "env", "event"].forEach(function (n) {
    idx[n] = header.indexOf(n);
    if (idx[n] < 0) missing.push(n);
  });
  if (missing.length) throw new Error("Sheet is missing columns: " + missing.join(", "));

  // Read only up to the last NEEDED column - the large payload JSON never enters memory.
  var width = Math.max(idx.ts, idx.session, idx.env, idx.event) + 1;
  var rows = sh.getRange(2, 1, last - 1, width).getValues();
  var skip = USE_MY_IDS ? myIds_(ss) : {};

  var perDay = {};
  var sessionsAll = {};
  var firstDay = {};
  var totals = {};

  for (var i = 0; i < rows.length; i++) {
    var ts = rows[i][idx.ts];
    var session = String(rows[i][idx.session] || "").trim();
    var env = rows[i][idx.env];
    var event = String(rows[i][idx.event] || "");
    if (env !== "prod") continue;
    if (!(ts instanceof Date)) continue; // probe rows and hand-pasted rows
    if (USE_MY_IDS && skip[session]) continue;

    var key = Utilities.formatDate(ts, tz, "yyyy-MM-dd");
    if (!perDay[key]) perDay[key] = { s: {}, c: {} };
    if (session) {
      sessionsAll[session] = 1;
      perDay[key].s[session] = 1;
    }
    if (!event) continue;
    if (firstDay[event] == null || key < firstDay[event]) firstDay[event] = key;
    perDay[key].c[event] = (perDay[key].c[event] || 0) + 1;
    totals[event] = (totals[event] || 0) + 1;
  }

  var activeDays = Object.keys(perDay).length;
  // Days with no events must exist as zero, not as a gap: a skipped day collapses on the
  // chart and a dead week looks like traffic.
  var keys = fillDays_(Object.keys(perDay).sort());
  var daily = keys.map(function (k) {
    var d = perDay[k] || { s: {}, c: {} };
    var c = {};
    EVENTS.forEach(function (ev) {
      c[ev] = firstDay[ev] != null && k >= firstDay[ev] ? d.c[ev] || 0 : null;
    });
    return { key: k, sessions: Object.keys(d.s).length, c: c };
  });

  var starts = totals[START_EVENT] || 0;
  var done = DONE_EVENT ? totals[DONE_EVENT] || 0 : null;
  return {
    generatedAt: Utilities.formatDate(new Date(), tz, "yyyy-MM-dd HH:mm"),
    events: EVENTS,
    kpis: {
      sessions: Object.keys(sessionsAll).length, // devices, not people
      days: activeDays, // days with activity, not the date range
      starts: starts,
      done: done,
      completionPct: DONE_EVENT && starts ? Math.round((done / starts) * 100) : null,
    },
    funnel: EVENTS.map(function (ev) {
      return { event: ev, n: totals[ev] || 0 };
    }),
    daily: daily,
  };
}

// Fill missing days between the first and last key (keys are already formatted in the
// Sheet's timezone; here we only count days, so UTC arithmetic is safe).
function fillDays_(keys) {
  if (keys.length < 2) return keys;
  var out = [];
  var day = 24 * 60 * 60 * 1000;
  var cur = Date.parse(keys[0] + "T00:00:00Z");
  var end = Date.parse(keys[keys.length - 1] + "T00:00:00Z");
  while (cur <= end) {
    out.push(new Date(cur).toISOString().slice(0, 10));
    cur += day;
  }
  return out;
}

// The team's own session ids, read dynamically: a new own device is one row in the Sheet,
// no code change.
function myIds_(ss) {
  var sh = ss.getSheetByName(MY_IDS_SHEET);
  if (!sh || sh.getLastRow() < 2) return {};
  var out = {};
  sh.getRange(2, 1, sh.getLastRow() - 1, 1)
    .getValues()
    .forEach(function (r) {
      var id = String(r[0] || "").trim();
      if (id) out[id] = 1;
    });
  return out;
}

function emptyPayload_(tz) {
  return {
    generatedAt: Utilities.formatDate(new Date(), tz, "yyyy-MM-dd HH:mm"),
    events: EVENTS,
    kpis: { sessions: 0, days: 0, starts: 0, done: DONE_EVENT ? 0 : null, completionPct: null },
    funnel: EVENTS.map(function (ev) {
      return { event: ev, n: 0 };
    }),
    daily: [],
  };
}
