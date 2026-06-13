"""Daily updater: append missing rows to 'TC diario OFICIAL' and 'TC diario MEP'.

Idempotent: only dates newer than the last real row and not already present are
written. Recomputes the FDM (end-of-month) flag across the month boundary.

Run: python -m update_daily        (uses Graph; needs env vars)
"""
from __future__ import annotations

import datetime as dt

import status
import validate
from fdm import fdm_flags
from graph_client import GraphExcel, from_excel_serial, to_excel_serial
from sources import ambito_mep, bna_oficial

DATE_FMT = "dd/mm/yyyy"


def _existing_dates(values: list[list], date_col: int) -> list[tuple[int, dt.date]]:
    """Return (row_index_0based, date) for rows that hold a real date."""
    out = []
    for i, row in enumerate(values):
        if len(row) <= date_col:
            continue
        cell = row[date_col]
        if isinstance(cell, (int, float)) and cell > 1:  # excel serial
            out.append((i, from_excel_serial(cell)))
    return out


def _update_sheet(gx: GraphExcel, sheet: str, ncols: int, date_col: int,
                  main_col: int, main_idx: int,
                  new_data: dict[dt.date, list], validator) -> tuple[int, object]:
    """main_col: 0-based sheet column of the comparison value (for prev lookup).
    main_idx: index of that value inside each source rec in new_data."""
    ur = gx.used_range(sheet)
    values = ur["values"]
    base_row = ur["rowIndex"]  # 0-based sheet row of values[0]
    existing = _existing_dates(values, date_col)
    have = {d for _, d in existing}

    last_date = max(have) if have else dt.date.min
    last_row0 = None
    prev_val = None
    if existing:
        last_row0, _ = max(existing, key=lambda t: t[1])
        prev_val = values[last_row0][main_col]

    new_dates = sorted(d for d in new_data if d > last_date and d not in have)
    if not new_dates:
        return 0, prev_val

    # validate sequentially, carrying forward the comparison value
    p = prev_val
    for d in new_dates:
        validator(new_data[d], p)
        p = new_data[d][main_idx]

    # FDM across boundary: combined tail = [last_date] + new_dates
    tail = ([last_date] if existing else []) + new_dates
    flags = fdm_flags(tail)
    boundary_flag = flags[0] if existing else None
    new_flags = flags[1:] if existing else flags

    # build rows (date as serial; FDM in last column)
    rows = []
    for d, f in zip(new_dates, new_flags):
        rec = list(new_data[d])
        rec_full = [d.year, d.month, to_excel_serial(d)] + rec + [f]
        rows.append(rec_full[:ncols] + [""] * (ncols - len(rec_full)))

    first_row = gx.append_rows(sheet, rows)
    # format the date column on the new rows
    last_row = first_row + len(rows) - 1
    date_letter = chr(ord("A") + date_col)
    gx.set_number_format(sheet, f"{date_letter}{first_row}:{date_letter}{last_row}",
                         DATE_FMT)

    # if the previous last row just became a month-end, flag it
    if boundary_flag == "FDM" and last_row0 is not None:
        fdm_letter = chr(ord("A") + ncols - 1)
        sheet_row = base_row + last_row0 + 1  # 1-based
        gx.set_range(sheet, f"{fdm_letter}{sheet_row}:{fdm_letter}{sheet_row}",
                     [["FDM"]])

    return len(rows), new_data[new_dates[-1]][-1]


def run() -> None:
    gx = GraphExcel()

    # --- TC diario OFICIAL: [Año Mes Fecha Compra Venta FDM] ---
    try:
        q = bna_oficial.fetch_billete()
        data = {q.date: [q.compra, q.venta]}

        def v_of(rec, prev):
            validate.check_oficial(rec[0], rec[1], prev)

        added, last = _update_sheet(gx, "TC diario OFICIAL", 6, 2,
                                    main_col=4, main_idx=1,
                                    new_data=data, validator=v_of)
        status.record("TC diario OFICIAL", ok=True, added=added, last_value=last,
                      message=f"+{added} rows")
    except Exception as e:  # noqa: BLE001
        status.record("TC diario OFICIAL", ok=False, message=str(e))

    # --- TC diario MEP: [Año Mes Fecha Referencia FDM] ---
    try:
        mep = ambito_mep.fetch_recent()
        data = {d: [v] for d, v in mep.items()}

        def v_mep(rec, prev):
            validate.check_rate("MEP", rec[0], prev)

        added, last = _update_sheet(gx, "TC diario MEP", 5, 2,
                                    main_col=3, main_idx=0,
                                    new_data=data, validator=v_mep)
        status.record("TC diario MEP", ok=True, added=added, last_value=last,
                      message=f"+{added} rows")
    except Exception as e:  # noqa: BLE001
        status.record("TC diario MEP", ok=False, message=str(e))


if __name__ == "__main__":
    run()
