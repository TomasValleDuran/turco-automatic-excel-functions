# turco — API de valores para Macro.xlsx

Una API que devuelve los últimos valores macro-económicos publicados en JSON,
listos para parsear. No hay página ni modificación automática del Excel: solo el
endpoint.

## Endpoint

`GET /api/data`  (también disponible en la raíz `/`)

Devuelve:

```json
{
  "fecha":   "2026-06-26",
  "oficial": { "compra": 1445, "venta": 1495 },
  "mep":     { "referencia": 1499.38 },
  "mensual": {
    "cpi": { "year": 2026, "month": 5, "value": 335.123 },
    "ipc": {
      "periodo": "2026-05-01",
      "columnas": ["NACIONAL","GBA","PAMPEANA","NEA","NOA","CUYO","PATAGONIA"],
      "valores": [11607.39, 11594.55, 11556.85, 11725.60, 11747.53, 11750.09, 11622.75]
    }
  }
}
```

| Campo | Fuente |
|---|---|
| `oficial` (compra/venta) | BNA "Billetes" (bna.com.ar/Personas) |
| `mep.referencia` | ámbito (JSON) |
| `mensual.cpi` | usinflationcalculator.com (índice del último mes) |
| `mensual.ipc` | INDEC `apendice4.xlsx`, tab `4.1.1 IPC NG` (7 regiones) |

## Cómo se actualizan los valores

- `/api/data` lee la caché en `web/data/*.json` (rápido y robusto: no le pega en
  vivo a las fuentes inestables en cada request).
- Una GitHub Action (`.github/workflows/update-data.yml`) corre
  `scripts/update_data.py` 1 vez al día, busca cada fuente, escribe el resultado
  en `web/data/daily.json` + `web/data/monthly.json` y lo commitea. Vercel
  redeploya y la API sirve los valores nuevos.
  - Si una fuente falla (p. ej. el error **104** del BNA) reintenta cada 15 min,
    hasta 5 veces, y **nunca pisa un valor bueno con un error**.
  - Se puede correr a mano desde GitHub → Actions → *Run workflow*.
- Funciones en vivo auxiliares (por si querés una fuente puntual sin caché):
  - `/api/daily`   → BNA + MEP (rápido)
  - `/api/monthly` → CPI + IPC (IPC baja ~11 MB de INDEC; lento)

## Deploy en Vercel
1. Importar el repo, **Root Directory = `web`**.
2. Deploy. `vercel.json` buildea `api/*.py` como funciones; `web/requirements.txt`
   trae las dependencias de scraping.

## Check local
```bash
python3 scripts/update_data.py daily     # regenera la caché (daily / monthly / all)
```
