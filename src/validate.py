"""Sanity checks run before any value is written to the workbook.

These guard the financial model against polluted source data (site layout
changes, parsing slips, transient garbage). A failed check raises and the
updater records an error instead of writing.
"""
from __future__ import annotations


class ValidationError(ValueError):
    pass


def check_rate(name: str, value: float, previous: float | None,
               max_pct: float = 0.15) -> None:
    """A positive FX rate that does not jump more than max_pct vs the prior value."""
    if value is None or value <= 0:
        raise ValidationError(f"{name}: non-positive rate {value!r}")
    if previous and previous > 0:
        change = abs(value - previous) / previous
        if change > max_pct:
            raise ValidationError(
                f"{name}: {value} moves {change:.1%} vs previous {previous} "
                f"(limit {max_pct:.0%})"
            )


def check_oficial(compra: float, venta: float, prev_venta: float | None) -> None:
    check_rate("OFICIAL venta", venta, prev_venta)
    if compra <= 0 or compra > venta:
        raise ValidationError(f"OFICIAL: implausible compra {compra} / venta {venta}")


def check_cpi(value: float, previous: float | None, max_pct: float = 0.05) -> None:
    """CPI index: positive and a modest month-over-month move."""
    if value is None or value <= 0:
        raise ValidationError(f"CPI: non-positive index {value!r}")
    if previous and previous > 0:
        change = abs(value - previous) / previous
        if change > max_pct:
            raise ValidationError(
                f"CPI: {value} moves {change:.1%} vs previous {previous}"
            )
