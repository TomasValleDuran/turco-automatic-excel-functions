"""Monthly updater (runs on the 20th): 'ARG IPC' and 'USA CPI'.

ARG IPC  - the sheet mirrors the INDEC tab '4.1.1 IPC NG' 1:1, so we append any
           period rows that exist in the source but not yet in the sheet.
USA CPI  - a Year x Month matrix; we fill only the empty month cells for recent
           years (and append a new year row if needed).
"""
from __future__ import annotations

import datetime as dt

import status
import validate
from graph_client import GraphExcel, _col_letter, to_excel_serial
from sources import arg_ipc, usa_cpi

DATE_FMT = "dd/mm/yyyy"


# --------------------------------------------------------------------------- #
# ARG IPC
# --------------------------------------------------------------------------- #
def _ipc_data_bounds(values: list[list]) -> tuple[int, int]:
    """Return (start_idx, count) of data rows within usedRange values."""
    start = None
    for i, row in enumerate(values):
        if row and str(row[0]).strip().lower() == "período":
            start = i + 2  # header row, then a code row, then data
            break
    if start is None:
        raise ValueError("ARG IPC: 'Período' header not found")
    count = 0
    for row in values[start:]:
        label = "" if not row else str(row[0]).strip().lower()
        if label.startswith("fuente"):
            break
        nums = [c for c in row[1:8] if isinstance(c, (int, float))]
        if label == "" and not nums:
            break
        count += 1
    return start, count


def _update_ipc(gx: GraphExcel) -> tuple[int, object]:
    source = arg_ipc.fetch_ipc()
    ur = gx.used_range("ARG IPC")
    start, count = _ipc_data_bounds(ur["values"])

    if len(source) <= count:
        last = source[-1][1] if source else None
        return 0, last

    new_rows_src = source[count:]
    # validate national index continuity vs last present value
    prev = ur["values"][start + count - 1][1] if count else None
    for rec in new_rows_src:
        validate.check_cpi(rec[1], prev, max_pct=0.20)
        prev = rec[1]

    rows = []
    for rec in new_rows_src:
        periodo = rec[0]
        cell0 = to_excel_serial(periodo) if isinstance(
            periodo, (dt.date, dt.datetime)) else periodo
        rows.append([cell0] + list(rec[1:8]))

    first = gx.append_rows("ARG IPC", rows)
    last = first + len(rows) - 1
    # format col A as date where the appended periods are dates
    if any(isinstance(r[0], (dt.date, dt.datetime)) for r in new_rows_src):
        gx.set_number_format("ARG IPC", f"A{first}:A{last}", DATE_FMT)
    return len(rows), new_rows_src[-1][1]


# --------------------------------------------------------------------------- #
# USA CPI
# --------------------------------------------------------------------------- #
def _update_cpi(gx: GraphExcel) -> tuple[int, object]:
    source = usa_cpi.fetch_cpi()
    ur = gx.used_range("USA CPI")
    values = ur["values"]
    base = ur["rowIndex"]

    year_row: dict[int, int] = {}
    header_idx = 0
    for i, row in enumerate(values):
        try:
            y = int(row[0])
        except (ValueError, TypeError):
            continue
        if 1900 <= y <= 2100:
            year_row[y] = i

    last_year_idx = max(year_row.values()) if year_row else 0
    written = 0
    last_val = None

    for year in sorted(source):
        months = source[year]
        if year in year_row:
            r0 = year_row[year]
            for m in range(1, 13):
                if m not in months:
                    continue
                existing = values[r0][m] if m < len(values[r0]) else None
                if isinstance(existing, (int, float)):
                    continue  # already filled
                prev = months.get(m - 1) or last_val
                validate.check_cpi(months[m], prev)
                sheet_row = base + r0 + 1
                col = _col_letter(m)
                gx.set_range("USA CPI", f"{col}{sheet_row}:{col}{sheet_row}",
                             [[months[m]]])
                written += 1
                last_val = months[m]
        else:
            # append a brand-new year row
            row_vals = [year] + [months.get(m, "") for m in range(1, 13)]
            gx.append_rows("USA CPI", [row_vals])
            written += sum(1 for m in range(1, 13) if m in months)
            if months:
                last_val = months[max(months)]

    return written, last_val


def run() -> None:
    gx = GraphExcel()
    for name, fn in (("ARG IPC", _update_ipc), ("USA CPI", _update_cpi)):
        try:
            added, last = fn(gx)
            status.record(name, ok=True, added=added, last_value=last,
                          message=f"+{added} values")
        except Exception as e:  # noqa: BLE001
            status.record(name, ok=False, message=str(e))


if __name__ == "__main__":
    run()
