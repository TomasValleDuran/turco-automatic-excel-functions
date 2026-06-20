#!/usr/bin/env python3
"""Fetch macro values and store them as JSON for the static page to display.

Runs from GitHub Actions once a day. The page no longer depends on the client
hitting flaky upstreams (e.g. BNA's 'Connection reset by peer' / error 104):
it just reads the last successfully stored value here.

Behaviour:
  - Retries each source up to MAX_ATTEMPTS times, RETRY_SECONDS apart, only
    re-fetching the ones still missing. This is what self-heals the BNA 104.
  - NEVER overwrites a good stored value with an error: if a source fails on
    every attempt, the previous value is kept untouched.
  - Daily values keep a per-day history (today, yesterday, ...); monthly keeps
    the latest only.

Usage:
  python scripts/update_data.py            # update daily + monthly
  python scripts/update_data.py daily      # only the daily TC (fast)
  python scripts/update_data.py monthly    # only CPI + IPC (slow INDEC download)
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "web" / "api"
DATA_DIR = ROOT / "web" / "data"
DAILY_JSON = DATA_DIR / "daily.json"
MONTHLY_JSON = DATA_DIR / "monthly.json"

MAX_ATTEMPTS = 5            # total tries per run, including the first
RETRY_SECONDS = 15 * 60     # wait between tries (only when something failed)
HISTORY_KEEP = 60           # daily entries to retain
AR_TZ = dt.timezone(dt.timedelta(hours=-3))  # Argentina, no DST


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, API_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def fetch_with_retries(fetchers: dict, label: str) -> dict:
    """Return {name: value} for every source that eventually succeeded.

    Missing keys = sources that failed all attempts (caller keeps old values).
    """
    results: dict = {}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        pending = [k for k in fetchers if k not in results]
        for name in pending:
            try:
                results[name] = fetchers[name]()
                print(f"[{label}] {name}: OK")
            except Exception as e:  # noqa: BLE001
                print(f"[{label}] {name}: FALLO (intento {attempt}/"
                      f"{MAX_ATTEMPTS}) -> {e}")
        if len(results) == len(fetchers):
            break
        if attempt < MAX_ATTEMPTS:
            print(f"[{label}] reintento en {RETRY_SECONDS // 60} min "
                  f"(faltan: {[k for k in fetchers if k not in results]})")
            time.sleep(RETRY_SECONDS)
    return results


def update_daily() -> bool:
    daily = _load_module("daily")
    got = fetch_with_retries(
        {"oficial": daily.fetch_oficial, "mep": daily.fetch_mep}, "daily")

    store = _load_json(DAILY_JSON, {"updated_at": None, "history": []})
    history = store.get("history", [])
    today = dt.datetime.now(AR_TZ).date().isoformat()

    entry = next((e for e in history if e.get("run_date") == today), None)
    if entry is None:
        entry = {"run_date": today}
        history.insert(0, entry)
    # Only overwrite a field when we have a fresh value; otherwise keep what was
    # there (which may itself be a value carried from an earlier good fetch).
    for key in ("oficial", "mep"):
        if key in got:
            entry[key] = got[key]

    history.sort(key=lambda e: e.get("run_date", ""), reverse=True)
    store["history"] = history[:HISTORY_KEEP]
    store["updated_at"] = dt.datetime.now(AR_TZ).isoformat(timespec="seconds")
    _write_json(DAILY_JSON, store)

    ok = len(got) == 2
    print(f"[daily] guardado en {DAILY_JSON} "
          f"({'completo' if ok else 'parcial — se conservaron valores previos'})")
    return ok


def update_monthly() -> bool:
    monthly = _load_module("monthly")
    got = fetch_with_retries(
        {"cpi": monthly.fetch_cpi, "ipc": monthly.fetch_ipc}, "monthly")

    store = _load_json(MONTHLY_JSON, {"updated_at": None})
    for key in ("cpi", "ipc"):
        if key in got:
            store[key] = got[key]
    store["updated_at"] = dt.datetime.now(AR_TZ).isoformat(timespec="seconds")
    _write_json(MONTHLY_JSON, store)

    ok = len(got) == 2
    print(f"[monthly] guardado en {MONTHLY_JSON} "
          f"({'completo' if ok else 'parcial — se conservaron valores previos'})")
    return ok


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    ok = True
    if which in ("all", "daily"):
        ok = update_daily() and ok
    if which in ("all", "monthly"):
        ok = update_monthly() and ok
    # Exit 0 even on partial failure: the page already shows last-good values and
    # we don't want to spam the Actions log as red for a transient upstream blip.
    return 0 if ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
