"""Vercel serverless function: trigger a GitHub Actions workflow on demand.

POST /api/trigger?type=daily   -> runs daily.yml
POST /api/trigger?type=monthly -> runs monthly.yml
The PAT lives only here (GH_TOKEN env var), never in the browser.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
from urllib.parse import parse_qs, urlparse


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        qs = parse_qs(urlparse(self.path).query)
        kind = (qs.get("type", ["daily"])[0] or "daily").lower()
        workflow = "monthly.yml" if kind == "monthly" else "daily.yml"

        repo = os.environ.get("GH_REPO", "")
        token = os.environ.get("GH_TOKEN", "")
        url = (f"https://api.github.com/repos/{repo}"
               f"/actions/workflows/{workflow}/dispatches")
        data = json.dumps({"ref": "main"}).encode()
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "macro-dashboard",
            "Content-Type": "application/json",
        })
        ok, msg = False, ""
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                ok = r.status in (201, 204)
        except Exception as e:  # noqa: BLE001
            msg = str(e)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": ok, "workflow": workflow,
                                     "error": msg}).encode())
