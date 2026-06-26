"""Endpoint único: devuelve los valores macro en JSON, listos para parsear.

Lee la caché (web/data/*.json) que la GitHub Action refresca a diario con
reintentos, así la respuesta es rápida y no depende de pegarle en vivo a las
fuentes inestables (p. ej. el error 104 del BNA) en cada request.

Forma de la respuesta:
{
  "fecha":   "2026-06-26",
  "oficial": { "compra": 1445, "venta": 1495 },
  "mep":     { "referencia": 1499.38 },
  "mensual": {
    "cpi": { "year": 2026, "month": 5, "value": 335.123 },
    "ipc": { "periodo": "2026-05-01", "columnas": [...], "valores": [...] }
  }
}
"""
from http.server import BaseHTTPRequestHandler
import datetime as dt
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def build() -> dict:
    daily = _load("daily.json")
    monthly = _load("monthly.json")

    latest = (daily.get("history") or [{}])[0]
    oficial = latest.get("oficial") or {}
    mep = latest.get("mep") or {}
    fecha = (oficial.get("date") or latest.get("run_date")
             or dt.date.today().isoformat())

    return {
        "fecha": fecha,
        "oficial": {
            "compra": oficial.get("compra"),
            "venta": oficial.get("venta"),
        },
        "mep": {
            "referencia": mep.get("value"),
        },
        "mensual": {
            "cpi": monthly.get("cpi"),
            "ipc": monthly.get("ipc"),
        },
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(build(), ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
