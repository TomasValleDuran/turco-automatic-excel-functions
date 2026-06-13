"""Vercel serverless function: return the latest status.json from the repo.

Reads GH_TOKEN / GH_REPO from environment (set in Vercel project settings) so
the token is never exposed to the browser. Stdlib only — no build deps.
"""
from http.server import BaseHTTPRequestHandler
import os
import urllib.request


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        repo = os.environ.get("GH_REPO", "")
        token = os.environ.get("GH_TOKEN", "")
        url = f"https://api.github.com/repos/{repo}/contents/status.json"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.raw",
            "User-Agent": "macro-dashboard",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read()
        except Exception:  # noqa: BLE001  (no status yet, bad token, etc.)
            body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
