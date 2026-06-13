"""Fetch MEP dollar history from ámbito.

Endpoint returns a JSON array of ["DD/MM/YYYY", "1450,36"] (comma decimal),
newest first. We normalize to {date: float}.
"""
from __future__ import annotations

import datetime as dt

import requests

URL = "https://mercados.ambito.com/dolarrava/mep/historico-general/{frm}/{to}"
HEADERS = {"User-Agent": "Mozilla/5.0 (macro-updater)"}


def fetch_mep(frm: dt.date, to: dt.date) -> dict[dt.date, float]:
    url = URL.format(frm=frm.isoformat(), to=to.isoformat())
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    out: dict[dt.date, float] = {}
    for item in rows:
        if not isinstance(item, list) or len(item) < 2:
            continue
        raw_date, raw_val = item[0], item[1]
        # skip header-ish rows
        try:
            d = dt.datetime.strptime(raw_date.strip(), "%d/%m/%Y").date()
        except (ValueError, AttributeError):
            continue
        val = float(str(raw_val).strip().replace(".", "").replace(",", "."))
        out[d] = val
    return out


def fetch_recent(days: int = 12) -> dict[dt.date, float]:
    today = dt.date.today()
    return fetch_mep(today - dt.timedelta(days=days), today)


if __name__ == "__main__":
    data = fetch_recent()
    for d in sorted(data):
        print(d, data[d])
