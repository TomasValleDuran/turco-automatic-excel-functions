"""End-of-month ('FDM') flag logic.

Convention observed in Macro.xlsx: within the daily sheets, the last business
day present for a month carries the literal string 'FDM'. A month is only
"closed" once a row from a later month exists, so the most recent row (current,
still-open month) never carries FDM.

Rule: row[i] is FDM iff a chronologically later row exists in a different
(year, month).
"""
from __future__ import annotations

import datetime as dt


def _ym(d: dt.date) -> tuple[int, int]:
    return (d.year, d.month)


def fdm_flags(dates: list[dt.date]) -> list[str]:
    """Return an FDM flag ('FDM' or '') aligned to `dates` (assumed sorted asc)."""
    flags = [""] * len(dates)
    for i in range(len(dates) - 1):
        if _ym(dates[i]) != _ym(dates[i + 1]):
            flags[i] = "FDM"
    return flags
