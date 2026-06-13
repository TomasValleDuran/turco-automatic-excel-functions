"""Simple, non-developer-friendly status dashboard (Streamlit Community Cloud).

Shows per-source freshness + last error from status.json (read from the GitHub
repo) and offers a "Run now" button that triggers the GitHub Actions workflow.

Streamlit secrets needed:
  github_repo   = "owner/macro-updater"
  github_token  = "<PAT with 'actions:write' / workflow scope>"
"""
from __future__ import annotations

import datetime as dt

import requests
import streamlit as st

REPO = st.secrets.get("github_repo", "")
TOKEN = st.secrets.get("github_token", "")
API = "https://api.github.com"

SOURCES = ["TC diario OFICIAL", "TC diario MEP", "ARG IPC", "USA CPI"]

st.set_page_config(page_title="Macro.xlsx — estado", page_icon="📈")
st.title("📈 Actualización de Macro.xlsx")


@st.cache_data(ttl=60)
def load_status() -> dict:
    url = f"{API}/repos/{REPO}/contents/status.json"
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Accept": "application/vnd.github.raw"}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 200:
        return r.json()
    return {}


def trigger(workflow: str) -> bool:
    url = f"{API}/repos/{REPO}/actions/workflows/{workflow}/dispatches"
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Accept": "application/vnd.github+json"}
    r = requests.post(url, headers=headers, json={"ref": "main"}, timeout=20)
    return r.status_code == 204


def _age(iso: str | None) -> str:
    if not iso:
        return "nunca"
    t = dt.datetime.fromisoformat(iso)
    delta = dt.datetime.now(dt.timezone.utc) - t
    h = int(delta.total_seconds() // 3600)
    return "hace <1 h" if h < 1 else f"hace {h} h"


status = load_status()
for name in SOURCES:
    s = status.get(name, {})
    ok = s.get("ok")
    icon = "✅" if ok else ("⚠️" if ok is False else "⬜")
    with st.container(border=True):
        st.subheader(f"{icon} {name}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Último valor", s.get("last_value", "—"))
        c2.metric("Última corrida", _age(s.get("last_run")))
        c3.metric("Filas agregadas", s.get("added", 0))
        if ok is False:
            st.error(s.get("message", "Error desconocido"))

st.divider()
col_a, col_b = st.columns(2)
if col_a.button("🔄 Actualizar diario ahora", use_container_width=True):
    st.success("Lanzado") if trigger("daily.yml") else st.error("Falló el disparo")
if col_b.button("🗓️ Actualizar mensual ahora", use_container_width=True):
    st.success("Lanzado") if trigger("monthly.yml") else st.error("Falló el disparo")

st.caption("Diario: 08:00 (L-V) · Mensual: día 20, 08:00 · hora de Argentina")
