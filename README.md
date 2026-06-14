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
- Static `web/index.html` + two Python serverless functions on **Vercel**:
  - `web/api/daily.py`   → BNA + MEP (fast)
  - `web/api/monthly.py` → CPI + IPC (IPC downloads ~11 MB from INDEC, so it runs
    only when you press the button; `maxDuration` is raised in `vercel.json`)
- No environment variables or credentials required.

## Deploy on Vercel
1. Import the repo, set **Root Directory = `web`**.
2. Deploy. `vercel.json` builds `api/*.py` as functions and serves `index.html`;
   `web/requirements.txt` provides the scraping deps.

## Local check
```bash
cd web/api
python3 -c "import importlib.util as u; s=u.spec_from_file_location('m','daily.py'); \
m=u.module_from_spec(s); s.loader.exec_module(m); print(m.fetch_oficial(), m.fetch_mep())"
```

## Full automation
The complete hands-off version — GitHub Actions writing straight into
`Macro.xlsx` via the Microsoft Graph API on a daily/monthly schedule, plus a
status dashboard — lives on the **`m365-automation`** branch. It needs M365
(Entra app + Graph permissions) and GitHub Actions secrets; see that branch's
README. Merge it into `main` once those credentials are available.
