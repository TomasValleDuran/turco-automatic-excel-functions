"""Scrape the BNA 'Billetes' US-dollar buy/sell quote from bna.com.ar/Personas.

The page renders a 'Cotización de Billetes' table server-side. We locate the
Dólar U.S.A row and return (compra, venta) as floats for the publication date.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

import requests
import urllib3
from bs4 import BeautifulSoup

URL = "https://www.bna.com.ar/Personas"
HEADERS = {"User-Agent": "Mozilla/5.0 (macro-updater)"}


@dataclass
class Quote:
    date: dt.date
    compra: float
    venta: float


def _num(text: str) -> float:
    # AR format: "1.450,0000" -> 1450.0
    return float(text.strip().replace(".", "").replace(",", "."))


def fetch_billete() -> Quote:
    # BNA serves a self-signed cert in its chain; relax TLS for this host only.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    resp = requests.get(URL, headers=HEADERS, timeout=30, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # The "Billetes" table contains a "Dolar U.S.A" row with Compra / Venta cells.
    date = _find_date(soup)
    for row in soup.find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if not cells:
            continue
        label = cells[0].lower()
        if "dolar" in label or "dólar" in label:
            nums = [c for c in cells[1:] if re.search(r"\d", c)]
            if len(nums) >= 2:
                return Quote(date=date, compra=_num(nums[0]), venta=_num(nums[1]))
    raise ValueError("Could not locate Dólar U.S.A billete row on BNA page")


def _find_date(soup: BeautifulSoup) -> dt.date:
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", soup.get_text())
    if m:
        d, mo, y = (int(x) for x in m.groups())
        return dt.date(y, mo, d)
    return dt.date.today()


if __name__ == "__main__":
    print(fetch_billete())
