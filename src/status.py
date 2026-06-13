"""Per-source run status, persisted as JSON for the dashboard to read.

The file is committed back to the repo by the GitHub Actions workflow so the
Vercel dashboard can show freshness and last error without any database.
"""
from __future__ import annotations

import datetime as dt
import json
import os

STATUS_PATH = os.environ.get("STATUS_PATH", "status.json")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load() -> dict:
    try:
        with open(STATUS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def record(source: str, *, ok: bool, message: str = "",
           added: int = 0, last_value=None) -> None:
    data = load()
    entry = data.get(source, {})
    entry["last_run"] = _now()
    entry["ok"] = ok
    entry["message"] = message
    entry["added"] = added
    if ok:
        entry["last_success"] = _now()
        if last_value is not None:
            entry["last_value"] = last_value
    data[source] = entry
    with open(STATUS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
