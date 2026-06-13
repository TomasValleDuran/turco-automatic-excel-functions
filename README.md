# macro-updater

Keeps the four data sheets in **Macro.xlsx** (hosted on OneDrive/SharePoint) up
to date automatically, and gives non-technical users a simple dashboard to watch
status and trigger a refresh on demand.

| Sheet | Source | Cadence |
|---|---|---|
| TC diario OFICIAL | BNA "Billetes" (bna.com.ar/Personas) | Daily, 08:00 ART (Mon–Fri) |
| TC diario MEP | ámbito MEP history (JSON) | Daily, 08:00 ART (Mon–Fri) |
| ARG IPC | INDEC `apendice4.xlsx`, tab `4.1.1 IPC NG` | Monthly, the 20th 08:00 ART |
| USA CPI | usinflationcalculator.com (CPI-U table) | Monthly, the 20th 08:00 ART |

The job edits cells **in place** through the Microsoft Graph Excel API, so all
formulas/charts/formatting in `MODELO`, `Evolución TC real`, etc. are untouched.
Updates are **idempotent**: only missing rows/values are written, and every
value passes a sanity check (`validate.py`) before being saved.

## How it runs

- **GitHub Actions** (free) is the always-on scheduler: `daily.yml` and
  `monthly.yml`. Both also accept manual `workflow_dispatch`.
- After each run, `status.json` is committed to the repo.
- **Streamlit Community Cloud** (free) hosts `dashboard/app.py`, which reads
  `status.json` and exposes **"Run now"** buttons.

## One-time setup

### 1. Entra ID (Azure AD) app — needs an M365 admin
1. Entra admin center → App registrations → New registration.
2. API permissions → Microsoft Graph → **Application** → `Files.ReadWrite.All`
   (use `Sites.ReadWrite.All` if the file lives on a SharePoint site) →
   **Grant admin consent**.
3. Certificates & secrets → new client secret (note the value).
4. Record **Tenant ID**, **Client ID**, **Client secret**.

### 2. Locate Macro.xlsx
Get the file's `driveId` + `itemId` via Graph Explorer or:
```
GET /drives/{driveId}/root:/path/to/Macro.xlsx
```
Record `GRAPH_DRIVE_ID` and `GRAPH_ITEM_ID`.

### 3. GitHub repo secrets
In the repo: Settings → Secrets and variables → Actions → add
`TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`, `GRAPH_DRIVE_ID`, `GRAPH_ITEM_ID`.

### 4. Dashboard (Streamlit Community Cloud)
Deploy `dashboard/app.py`. In app **Secrets** add:
```toml
github_repo  = "your-org/macro-updater"
github_token = "ghp_…"   # fine-grained PAT, Actions: write
```

## Local testing

```bash
pip install -r requirements.txt
cd src
python -m tests_logic            # pure logic (FDM, validation, helpers)
python -m sources.ambito_mep     # live source dry-runs (no credentials needed)
python -m sources.bna_oficial
python -m sources.usa_cpi
python -m sources.arg_ipc
# Full Graph run (needs the env vars from step 1–3 exported):
python -m update_daily
python -m update_monthly
```
Tip: point `GRAPH_ITEM_ID` at a **copy** of the workbook for the first end-to-end
test, then verify the model sheets are intact before going live.

## Fallback

If a source site changes its layout, the affected updater records an error
(visible on the dashboard) and writes nothing — users can enter that one value by
hand. Fix the relevant `src/sources/*.py` parser and re-run.
