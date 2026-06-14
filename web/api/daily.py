"""Daily values for copy-paste: BNA 'Billetes' (OFICIAL) + ámbito MEP.

Returns the latest available value for each, ready to paste into Macro.xlsx.
Stdlib + requests/bs4 only; both work in a couple of seconds.
"""
from http.server import BaseHTTPRequestHandler
import datetime as dt
import json
import re

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
UA = {"User-Agent": "Mozilla/5.0 (macro-tool)"}


def _num(t: str) -> float:
    return float(t.strip().replace(".", "").replace(",", "."))


def fetch_oficial() -> dict:
    r = requests.get("https://www.bna.com.ar/Personas", headers=UA,
                     timeout=20, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", soup.get_text())
    date = (f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
            if m else dt.date.today().isoformat())
    for row in soup.find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if cells and ("dolar" in cells[0].lower() or "dólar" in cells[0].lower()):
            nums = [c for c in cells[1:] if re.search(r"\d", c)]
            if len(nums) >= 2:
                return {"date": date, "compra": _num(nums[0]),
                        "venta": _num(nums[1])}
    raise ValueError("No se encontró la fila del dólar en BNA")


def fetch_mep() -> dict:
    today = dt.date.today()
    frm = today - dt.timedelta(days=12)
    url = ("https://mercados.ambito.com/dolarrava/mep/historico-general/"
           f"{frm.isoformat()}/{today.isoformat()}")
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    best = None
    for it in r.json():
        if not isinstance(it, list) or len(it) < 2:
            continue
        try:
            d = dt.datetime.strptime(it[0].strip(), "%d/%m/%Y").date()
        except (ValueError, AttributeError):
            continue
        v = float(str(it[1]).replace(".", "").replace(",", "."))
        if best is None or d > best[0]:
            best = (d, v)
    if not best:
        raise ValueError("Sin datos MEP")
    return {"date": best[0].isoformat(), "value": best[1]}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        out = {}
        for key, fn in (("oficial", fetch_oficial), ("mep", fetch_mep)):
            try:
                out[key] = fn()
            except Exception as e:  # noqa: BLE001
                out[key] = {"error": str(e)}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(out).encode())
