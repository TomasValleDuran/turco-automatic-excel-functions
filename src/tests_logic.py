"""Pure-logic tests that need no network or Graph credentials.

Run: python -m tests_logic
"""
import datetime as dt

import validate
from fdm import fdm_flags
from graph_client import _col_index, _col_letter, _n_cells, to_excel_serial


def test_fdm():
    dates = [dt.date(2020, 3, 30), dt.date(2020, 3, 31),
             dt.date(2020, 4, 1), dt.date(2020, 4, 2)]
    assert fdm_flags(dates) == ["", "FDM", "", ""]
    # single open month -> no flag
    assert fdm_flags([dt.date(2026, 6, 11)]) == [""]


def test_col_helpers():
    assert _col_letter(0) == "A"
    assert _col_letter(5) == "F"
    assert _col_letter(26) == "AA"
    assert _col_index("A") == 0
    assert _col_index("F") == 5
    assert _col_index("AA") == 26
    assert _n_cells("A5:A9") == 5
    assert _n_cells("B3") == 1


def test_excel_serial():
    # 2003-01-02 is the first OFICIAL row; verify round-trippable & known anchor
    assert to_excel_serial(dt.date(1899, 12, 31)) == 1
    assert to_excel_serial(dt.date(2026, 6, 12)) == 46185


def test_validate():
    validate.check_oficial(1400, 1450, 1465)          # ok
    validate.check_rate("MEP", 1450.36, 1449.23)      # ok
    validate.check_cpi(335.123, 333.02)               # ok
    for bad in (
        lambda: validate.check_oficial(1400, 1450, 100),   # 14x jump
        lambda: validate.check_oficial(1500, 1450, 1465),  # compra>venta
        lambda: validate.check_rate("MEP", -5, 1449),      # negative
    ):
        try:
            bad()
        except validate.ValidationError:
            continue
        raise AssertionError("expected ValidationError")


if __name__ == "__main__":
    test_fdm()
    test_col_helpers()
    test_excel_serial()
    test_validate()
    print("all logic tests passed")
