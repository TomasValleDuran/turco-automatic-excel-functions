"""Scrape CPI-U monthly index from usinflationcalculator.com.

The page has an HTML table: first column = Year, columns 2..13 = Jan..Dec,
plus trailing average columns we ignore. Returns {year: {month: value}}.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

URL = (
    "https://www.usinflationcalculator.com/inflation/"
    "consumer-price-index-and-annual-percent-changes-from-1913-to-2008/"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (macro-updater)"}


def _to_float(text: str) -> float | None:
    text = text.strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fetch_cpi() -> dict[int, dict[int, float]]:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    out: dict[int, dict[int, float]] = {}
    for row in soup.find_all("tr"):
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if not cells:
            continue
        year = None
        try:
            year = int(cells[0])
        except ValueError:
            continue
        if not (1900 <= year <= 2100):
            continue
        months: dict[int, float] = {}
        for m in range(1, 13):
            if m < len(cells):
                v = _to_float(cells[m])
                if v is not None:
                    months[m] = v
        if months:
            out[year] = months
    return out


if __name__ == "__main__":
    data = fetch_cpi()
    for y in sorted(data)[-3:]:
        print(y, data[y])
