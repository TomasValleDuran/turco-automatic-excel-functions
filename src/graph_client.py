"""Microsoft Graph Excel client (app-only, client-credentials).

Edits cells *in place* in the OneDrive/SharePoint-hosted Macro.xlsx via the
Graph workbook API, so every formula/chart/format in the rest of the model is
preserved (no download/rewrite/upload).

Required environment variables:
  TENANT_ID, CLIENT_ID, CLIENT_SECRET   - Entra ID app (app permission
                                          Files.ReadWrite.All, admin-consented)
  GRAPH_DRIVE_ID, GRAPH_ITEM_ID         - locator of Macro.xlsx
"""
from __future__ import annotations

import os

import msal
import requests

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPE = ["https://graph.microsoft.com/.default"]


class GraphExcel:
    def __init__(self) -> None:
        self.tenant = os.environ["TENANT_ID"]
        self.client_id = os.environ["CLIENT_ID"]
        self.secret = os.environ["CLIENT_SECRET"]
        self.drive = os.environ["GRAPH_DRIVE_ID"]
        self.item = os.environ["GRAPH_ITEM_ID"]
        self._token: str | None = None

    # --- auth ---------------------------------------------------------------
    def token(self) -> str:
        if self._token:
            return self._token
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=f"https://login.microsoftonline.com/{self.tenant}",
            client_credential=self.secret,
        )
        res = app.acquire_token_for_client(scopes=SCOPE)
        if "access_token" not in res:
            raise RuntimeError(f"Graph auth failed: {res.get('error_description')}")
        self._token = res["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token()}",
                "Content-Type": "application/json"}

    @property
    def _book(self) -> str:
        return f"{GRAPH}/drives/{self.drive}/items/{self.item}/workbook"

    # --- reads --------------------------------------------------------------
    def used_range(self, sheet: str) -> dict:
        """Return {'values', 'address', 'rowIndex', 'rowCount', 'columnCount'}."""
        url = (f"{self._book}/worksheets/{requests.utils.quote(sheet)}/usedRange"
               "?$select=values,address,rowIndex,rowCount,columnCount")
        r = requests.get(url, headers=self._headers(), timeout=60)
        r.raise_for_status()
        return r.json()

    # --- writes -------------------------------------------------------------
    def set_range(self, sheet: str, address: str, values: list[list]) -> None:
        """PATCH a range. `address` is sheet-local, e.g. 'A1830:E1830'."""
        url = (f"{self._book}/worksheets/{requests.utils.quote(sheet)}"
               f"/range(address='{address}')")
        r = requests.patch(url, headers=self._headers(),
                           json={"values": values}, timeout=60)
        r.raise_for_status()

    def set_number_format(self, sheet: str, address: str, fmt: str) -> None:
        """Apply a number format (e.g. 'dd/mm/yyyy') to a range."""
        url = (f"{self._book}/worksheets/{requests.utils.quote(sheet)}"
               f"/range(address='{address}')")
        n = _n_cells(address)
        r = requests.patch(url, headers=self._headers(),
                           json={"numberFormat": [[fmt]] * n}, timeout=60)
        r.raise_for_status()

    def append_rows(self, sheet: str, rows: list[list], start_col: str = "A") -> int:
        """Append `rows` below the current used range. Returns first row written."""
        if not rows:
            return 0
        ur = self.used_range(sheet)
        first_row = ur["rowIndex"] + ur["rowCount"] + 1  # 1-based, row after used
        end_col = _col_letter(_col_index(start_col) + len(rows[0]) - 1)
        last_row = first_row + len(rows) - 1
        self.set_range(sheet, f"{start_col}{first_row}:{end_col}{last_row}", rows)
        return first_row


def to_excel_serial(d) -> int:
    """date/datetime -> Excel serial day number (1900 date system)."""
    import datetime as _dt
    base = _dt.date(1899, 12, 30)
    if isinstance(d, _dt.datetime):
        d = d.date()
    return (d - base).days


def from_excel_serial(n: float):
    import datetime as _dt
    return _dt.date(1899, 12, 30) + _dt.timedelta(days=int(n))


def _n_cells(address: str) -> int:
    """Count rows in a single-column address like 'A5:A9' (-> 5)."""
    if ":" not in address:
        return 1
    a, b = address.split(":")
    r1 = int("".join(c for c in a if c.isdigit()))
    r2 = int("".join(c for c in b if c.isdigit()))
    return abs(r2 - r1) + 1


def _col_index(letter: str) -> int:
    idx = 0
    for ch in letter.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _col_letter(idx: int) -> str:
    s = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        s = chr(ord("A") + rem) + s
    return s
