# turco — valores para Macro.xlsx 

A small web tool that fetches the latest published macro-economic values and
presents them **ready to copy-paste** into `Macro.xlsx`. It's the interim step
while full automation is finished.

## What it shows
| Sección | Fuente | Valor |
|---|---|---|
| TC diario OFICIAL | BNA "Billetes" (bna.com.ar/Personas) | Compra / Venta |
| TC diario MEP | ámbito (JSON) | Referencia |
| USA CPI | usinflationcalculator.com | Índice del último mes |
| ARG IPC | INDEC `apendice4.xlsx`, tab `4.1.1 IPC NG` | Última fila (7 regiones) |

Each card has a **Copiar** button that puts the value(s) on the clipboard as
tab-separated text, so pasting drops them straight into the right cells/row.

## How it works (no secrets, no M365)
- **Auto-update (default):** a GitHub Action (`.github/workflows/update-data.yml`)
  runs `scripts/update_data.py` once a day, fetches every source and writes the
  results to `web/data/daily.json` + `web/data/monthly.json`, then commits them.
  Vercel serves those JSON files statically and `index.html` just displays them —
  so the page no longer depends on the client hitting a flaky upstream.
  - If a source fails (e.g. BNA's `Connection reset by peer` / error **104**),
    the script retries every 15 min, up to 5 times, and **never overwrites a good
    stored value with an error** — the page keeps showing the last valid number.
  - `daily.json` keeps a per-day **history** (today, yesterday, …); the page shows
    the latest plus a "Ver historial" table.
- **Manual fetch is still available:**
  - each card has a *↻ Refrescar en vivo* button that calls the live API;
  - the Action can be run on demand from GitHub → Actions → *Run workflow*.
- Live Python serverless functions on **Vercel** (used by the manual buttons):
  - `web/api/daily.py`   → BNA + MEP (fast)
  - `web/api/monthly.py` → CPI + IPC (IPC downloads ~11 MB from INDEC; slow)
- No environment variables or credentials required (the Action commits with the
  built-in `GITHUB_TOKEN`).

## Deploy on Vercel
1. Import the repo, set **Root Directory = `web`**.
2. Deploy. `vercel.json` builds `api/*.py` as functions and serves `index.html`;
   `web/requirements.txt` provides the scraping deps.

## Local check
```bash
# regenerate the stored JSON locally (same code the Action runs)
python3 scripts/update_data.py daily     # or: monthly / all
```

## Full automation
The complete hands-off version — GitHub Actions writing straight into
`Macro.xlsx` via the Microsoft Graph API on a daily/monthly schedule, plus a
status dashboard — lives on the **`m365-automation`** branch. It needs M365
(Entra app + Graph permissions) and GitHub Actions secrets; see that branch's
README. Merge it into `main` once those credentials are available.
