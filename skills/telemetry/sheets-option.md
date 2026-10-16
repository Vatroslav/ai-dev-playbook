# telemetry: Google Sheet + Apps Script collector

Purpose: a free, serverless collector for static apps without a backend: one Google Sheet plus one Apps Script project per app, a public write endpoint, a counts-only health endpoint and an aggregates-only dashboard.
Read when: the telemetry skill picked the Sheets option.

Templates: [templates/sheets/](templates/sheets/) (`Code.js` collector, `dashboard.js` + `Index.html` dashboard, `appsscript.json` manifest). Keep the script code in the repo under `metrics/apps-script/` and sync it with `clasp`; never edit in the web editor (the next `clasp push` replaces the whole online project).

## Preconditions

- `clasp --version` shows 3.x (`npm install -g @google/clasp` otherwise).
- `clasp show-authorized-user` shows the team's shared telemetry Google account, so every teammate can reach the Sheet and the deployments. Not logged in: the human runs `clasp login` and **ticks every scope checkbox** on the consent screen; otherwise login "succeeds" and the first push fails.
- The Apps Script API is enabled for that account (Apps Script settings page, user settings).

## Steps

1. **Create the project** (the folder must be empty):
   ```bash
   mkdir -p metrics/apps-script && cd metrics/apps-script
   clasp create-script --type sheets --title "<App> telemetry" --rootDir .
   ```
   The script id is `scriptId` in `.clasp.json`; the Sheet id is `parentId` (or from the printed URL). Delete the generated `Code.js` / `appsscript.json`; the templates replace them.
2. **Collector:** copy `templates/sheets/appsscript.json` and `templates/sheets/Code.js`; set `SHEET_ID`. App-specific columns go at the END of `HEADER`, with the values at the end of `appendRow`. `clasp push`.
3. **Owner consent (manual, once):** `clasp open-script`; the human selects the `probe` function, clicks Run and completes Google's dialog (Advanced, then continue: the project is unverified). Why: without it the public URL answers 403 to everyone, including the team. Wait for their confirmation.
4. **Collector deployment:** `clasp create-deployment --description "collector"` prints a deployment id; the URL is `https://script.google.com/macros/s/<deploymentId>/exec`. Check: `curl -s -L "<url>?health=1"` returns `{"ok":true,...}`. An HTML "you need access" page means step 3 is not done.
5. **Client:** put the URL into `ENDPOINT` in `metrics.js` (SKILL.md Step 3).
6. **Verify:** SKILL.md Step 4. Probe rows may be deleted from the Sheet afterwards.
7. **Dashboard:** copy `templates/sheets/dashboard.js` and `templates/sheets/Index.html`; set `EVENTS`, `START_EVENT`, `DONE_EVENT`, `USE_MY_IDS`. Never redeclare `SHEET_ID` / `SHEET_NAME` (a duplicate `const` breaks the whole project). Own-session filter: a tab named `my ids` with one session id per row in column A from row 2; a teammate's new device is one new row, no code change. `clasp push`, then `clasp create-deployment --description "dashboard v1"`: a SEPARATE deployment. Apps Script serves the page in a sandboxed cross-origin iframe that browser automation can't inspect; send the human the URL to check by eye.
8. **Record** in `metrics/README.md`: script id, Sheet id, collector URL, dashboard URL, event table. None of these are secrets, but keep the Sheet itself shared only with the team.

## Traps

- **Push is not live.** A web-app deployment serves a frozen version. After `clasp push`, update the deployment: `clasp list-deployments`, then `clasp update-deployment <deploymentId>`. Test on the `@HEAD` deployment first. Scopes added to the manifest also take effect only after a redeploy.
- **Never update the collector deployment whose URL is baked into the shipped app** unless the change is to the collector itself and was tested on `@HEAD`; never delete it. Dashboard changes go to the dashboard deployment only. Both URLs end in `/exec`, so label them in `metrics/README.md`.
- **Web client must use `mode: "no-cors"` and `text/plain`.** Apps Script does not answer CORS preflight requests; JSON content type triggers one and the event is lost silently.
- **Dashboard empty:** all rows are `dev`; your own id is filtered; `ts` stored as text (hand-pasted rows are skipped on purpose).
- **Timezones:** the collector aligns the Sheet's timezone to the script's on every write. The health output shows both; when auditing compare UTC offsets, not zone names (names get normalised).
- **Quotas:** Apps Script has daily execution quotas. This option fits prototypes and small launches; move to the own-backend option before the volume gets serious.

## Boundaries

- One Sheet and one script project per app; never point two apps at one collector.
- The dashboard returns aggregates only; row contents and session ids never leave the Sheet.
- No store or app deploys from here.
